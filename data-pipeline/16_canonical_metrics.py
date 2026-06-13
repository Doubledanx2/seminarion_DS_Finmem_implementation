"""Stage-11 Part A/B: CANONICAL metrics — the single source of truth for the deck.

Convention (documented, applied to EVERY series identically):
  - prices: FULL env series incl. the terminal day (data/03_model_input/<t>.pkl),
    NOT the portfolio series (which ends one day early).
  - position: carry-forward, unit long-only {0,+1}. buy=enter/keep, sell=exit,
    hold=carry. Held INTO the next trading day.
  - daily return: position_t * SIMPLE next-day return (P[t+1]/P[t]-1).
  - costs: cost_bps/1e4 * |pos_t - pos_{t-1}| subtracted (turnover drag).
  - aggregation: COMPOUNDED ( prod(1+r)-1 ). Sharpe/Sortino/vol annualized x sqrt(252).
  - B&H: position == 1 every day.
This REPLACES the buggy 07_metrics_v2.strategy_returns (raw decision as position ->
hold=flat, sell=SHORT, log returns), which inflated every cell. See 15_reconcile.py.
"""
import os
import sys
import pickle
import datetime

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.getcwd())
TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
TD = 252


def env_prices(ticker):
    """FULL test-window price series incl. the terminal day (2026-06-01). Reads the env
    pickle directly — NOT portfolio.market_price_series, which ends one decision-day
    early and dropped the −4.57% TSLA move on 2026-06-01 (the dominant bug, Stage 11)."""
    env = pickle.load(open(f"data/03_model_input/{ticker.lower()}.pkl", "rb"))
    days = sorted(d for d in env if d.year == 2026
                  and datetime.date(2026, 1, 2) <= d <= datetime.date(2026, 6, 1))
    return pd.Series({d: float(env[d]["price"][ticker]) for d in days})


def assert_terminal_day(ticker):
    """MANDATORY regression (Dan): compounded B&H must equal P[last]/P[first]-1, i.e.
    the series must include the final test day. Fails the run otherwise."""
    px = env_prices(ticker)
    bh_compound = float(np.prod(1 + bh_returns(ticker, 0.0)) - 1)
    identity = float(px.iloc[-1] / px.iloc[0] - 1)
    assert abs(bh_compound - identity) < 1e-6, (
        f"{ticker}: B&H {bh_compound:.6f} != P[last]/P[first]-1 {identity:.6f} "
        f"(terminal-day truncation!) first={px.index[0]} last={px.index[-1]}")
    return px.index[0], px.index[-1], identity


def decisions(tag):
    sd = pickle.load(open(f"data/07_test_model_output/{tag}/agent_1/state_dict.pkl", "rb"))
    return pd.Series({d: r.get("investment_decision", "hold")
                      for d, r in sd["reflection_result_series_dict"].items()
                      if d.year == 2026}).sort_index()


def carry_position(dec):
    h, out = 0, {}
    for d, a in dec.items():
        h = 1 if a == "buy" else (0 if a == "sell" else h)
        out[d] = h
    return pd.Series(out)


def daily_returns(pos, px, cost_bps=0.0):
    p = pos.reindex(px.index).ffill().fillna(0.0)
    fwd = px.shift(-1) / px - 1.0
    turn = (p - p.shift(1).fillna(0.0)).abs()
    r = (p * fwd - cost_bps / 1e4 * turn).dropna()
    return r


def metrics(r, bh_r=None):
    if len(r) == 0:
        return {}
    cum = float(np.prod(1 + r) - 1)
    ann = float((1 + cum) ** (TD / len(r)) - 1)
    vol = float(r.std(ddof=1) * np.sqrt(TD))
    sd = r.std(ddof=1)
    sharpe = float(r.mean() / sd * np.sqrt(TD)) if sd > 0 else np.nan
    downside = r[r < 0].std(ddof=1)
    sortino = float(r.mean() / downside * np.sqrt(TD)) if downside and downside > 0 else np.nan
    eq = (1 + r).cumprod()
    mdd = float((eq / eq.cummax() - 1).min())
    out = {"cum_return": cum, "ann_return": ann, "ann_vol": vol, "sharpe": sharpe,
           "sortino": sortino, "max_drawdown": mdd, "n_days": len(r),
           "mean_daily": float(r.mean()), "median_daily": float(r.median())}
    if bh_r is not None:
        a, b = r.align(bh_r, join="inner")
        if len(a) > 2 and b.std() > 0:
            beta, alpha = np.polyfit(b.values, a.values, 1)
            out["beta_vs_bh"] = float(beta)
            out["alpha_ann"] = float(alpha * TD)
    return out


def series_for(tag, ticker, cost_bps=0.0):
    px = env_prices(ticker)
    pos = carry_position(decisions(tag))
    return daily_returns(pos, px, cost_bps), px, pos


def bh_returns(ticker, cost_bps=0.0):
    px = env_prices(ticker)
    return daily_returns(pd.Series(1, index=px.index), px, cost_bps)


def turnover_and_long(tag):
    pos = carry_position(decisions(tag))
    p = pos.values.astype(float)
    turn = int(np.abs(np.diff(np.concatenate([[0], p]))).sum())
    pct_long = float((p > 0).mean())
    return turn, pct_long


def row_for(label, tag, ticker, as_shipped=False):
    px = env_prices(ticker)
    bh0 = bh_returns(ticker, 0.0)
    if as_shipped:
        sd = pickle.load(open("data/07_test_model_output/TSLA/agent_1/state_dict.pkl", "rb"))
        dec = pd.Series({d: r.get("investment_decision", "hold")
                         for d, r in sd["reflection_result_series_dict"].items()
                         if d.year == 2026}).sort_index()
        pos = carry_position(dec)
    else:
        pos = carry_position(decisions(tag))
    r0 = daily_returns(pos, px, 0.0)
    r10 = daily_returns(pos, px, 10.0)
    m0, m10 = metrics(r0, bh0), metrics(r10, bh0)
    turn, pct_long = turnover_and_long(tag) if not as_shipped else (
        int(np.abs(np.diff(np.concatenate([[0], pos.values.astype(float)]))).sum()),
        float((pos.values > 0).mean()))
    return {"ticker": ticker, "strategy": label,
            "cr_0": m0["cum_return"], "cr_10": m10["cum_return"],
            "ann_return_0": m0["ann_return"], "ann_vol_0": m0["ann_vol"],
            "sharpe_0": m0["sharpe"], "sharpe_10": m10["sharpe"],
            "sortino_0": m0["sortino"], "mdd_0": m0["max_drawdown"], "mdd_10": m10["max_drawdown"],
            "alpha_ann_0": m0.get("alpha_ann"), "beta_vs_bh_0": m0.get("beta_vs_bh"),
            "turnover": turn, "pct_days_long": pct_long}, r0


def bh_row(ticker):
    px = env_prices(ticker)
    r0, r10 = bh_returns(ticker, 0.0), bh_returns(ticker, 10.0)
    m0, m10 = metrics(r0, r0), metrics(r10, r0)
    return {"ticker": ticker, "strategy": "BuyHold",
            "cr_0": m0["cum_return"], "cr_10": m10["cum_return"],
            "ann_return_0": m0["ann_return"], "ann_vol_0": m0["ann_vol"],
            "sharpe_0": m0["sharpe"], "sharpe_10": m10["sharpe"],
            "sortino_0": m0["sortino"], "mdd_0": m0["max_drawdown"], "mdd_10": m10["max_drawdown"],
            "alpha_ann_0": 0.0, "beta_vs_bh_0": 1.0, "turnover": 1, "pct_days_long": 1.0}, r0


if __name__ == "__main__":
    print("TERMINAL-DAY REGRESSION (B&H == P[last]/P[first]-1):")
    for t in TICKERS:
        first, last, idn = assert_terminal_day(t)
        print(f"  {t}: {first}..{last}  B&H={idn*100:+.2f}%  OK")
    print()
    rows, ours_pool, nomem_pool, bh_pool, ours_for_nm = [], [], [], [], []
    for t in TICKERS:
        ro, r_o = row_for("FinMem-Ours", f"{t}_ours", t); rows.append(ro)
        ours_pool.append(r_o)
        bh = bh_row(t); rows.append(bh[0]); bh_pool.append(bh[1])
        nm_tag = f"{t}_ours_nomem"
        if os.path.exists(f"data/07_test_model_output/{nm_tag}/agent_1/state_dict.pkl"):
            rn, r_n = row_for("No-memory", nm_tag, t); rows.append(rn)
            common = r_o.index.intersection(r_n.index)
            nomem_pool.append(r_n.reindex(common)); ours_for_nm.append(r_o.reindex(common))
        if t == "TSLA" and os.path.exists("data/07_test_model_output/TSLA/agent_1/state_dict.pkl"):
            ra, _ = row_for("As-shipped", "TSLA", t, as_shipped=True); rows.append(ra)

    df = pd.DataFrame(rows)
    os.makedirs("data/09_results", exist_ok=True)
    df.to_csv("data/09_results/metrics_canonical.csv", index=False)

    # pooled stats
    def pooled_wilcoxon(a_list, b_list):
        a = pd.concat(a_list).reset_index(drop=True)
        b = pd.concat(b_list).reset_index(drop=True)
        d = (a - b).dropna(); d = d[d != 0]
        if len(d) < 10:
            return None
        s, p = stats.wilcoxon(d)
        return len(d), float(p), float(d.median())

    w_bh = pooled_wilcoxon(ours_pool, bh_pool)
    w_nm = pooled_wilcoxon(ours_for_nm, nomem_pool)

    def block_bootstrap_ci(r, block=10, n=5000, seed=42):
        rng = np.random.default_rng(seed); x = r.to_numpy(); N = len(x)
        block = max(2, min(block, N // 2))
        nb = int(np.ceil(N / block)); out = np.empty(n)
        for i in range(n):
            s = rng.integers(0, N - block + 1, size=nb)
            samp = np.concatenate([x[k:k + block] for k in s])[:N]
            sd = samp.std(ddof=1)
            out[i] = samp.mean() / sd * np.sqrt(TD) if sd > 0 else np.nan
        return float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))

    # markdown
    M = ["# Canonical metrics — FinMem-Ours (audited, Stage 11)\n",
         "**Convention:** simple daily returns, position = carry-forward unit long-only "
         "{0,+1} (buy=enter/keep, sell=exit, hold=carry) × next-day move, compounded, on "
         "the FULL env price series incl. the terminal day. Costs = bps × turnover. "
         "This SUPERSEDES the earlier RESULTS, which used raw decisions as the position "
         "(hold=flat, sell=SHORT) + log returns and inflated every cell (see 15_reconcile.py).\n"]
    M.append("| Ticker | Strategy | CR 0bps | CR 10bps | Ann.ret | Ann.vol | Sharpe | Sortino | MaxDD | alpha(ann) | beta | turn | %long |")
    M.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        def f(x, pct=True):
            if x is None or (isinstance(x, float) and np.isnan(x)):
                return "—"
            return f"{x*100:+.1f}%" if pct else f"{x:.2f}"
        M.append(f"| {r['ticker']} | {r['strategy']} | {f(r['cr_0'])} | {f(r['cr_10'])} | "
                 f"{f(r['ann_return_0'])} | {f(r['ann_vol_0'])} | {f(r['sharpe_0'],0)} | "
                 f"{f(r['sortino_0'],0)} | {f(r['mdd_0'])} | {f(r.get('alpha_ann_0'))} | "
                 f"{f(r.get('beta_vs_bh_0'),0)} | {r['turnover']} | {f(r['pct_days_long'])} |")
    # means
    o = df[df.strategy == "FinMem-Ours"]; nm = df[df.strategy == "No-memory"]; bh = df[df.strategy == "BuyHold"]
    M.append(f"\n## Means (cum return 0bps)\n")
    M.append(f"- FinMem-Ours **{o['cr_0'].mean()*100:+.1f}%** · No-memory **{nm['cr_0'].mean()*100:+.1f}%** "
             f"· Buy&Hold **{bh['cr_0'].mean()*100:+.1f}%**")
    M.append(f"- Mean Sharpe: Ours {o['sharpe_0'].mean():.2f} · No-mem {nm['sharpe_0'].mean():.2f} "
             f"· B&H {bh['sharpe_0'].mean():.2f}")
    nm_wins = int((nm.set_index('ticker')['cr_0'] > o.set_index('ticker')['cr_0']).sum())
    M.append(f"- No-memory > FinMem-Ours on **{nm_wins}/5** tickers (cum return).")
    if w_bh:
        M.append(f"\n**Pooled Wilcoxon** Ours vs B&H (n={w_bh[0]}): p={w_bh[1]:.4f}, median daily edge {w_bh[2]*1e4:+.1f} bps.")
    if w_nm:
        M.append(f"**Pooled Wilcoxon** Ours vs No-memory (n={w_nm[0]}): p={w_nm[1]:.4f}, "
                 f"median daily memory effect {w_nm[2]*1e4:+.1f} bps (neg ⇒ memory hurt).")
    lo, hi = block_bootstrap_ci(pd.concat(ours_pool))
    M.append(f"Bootstrap 95% CI on pooled Ours daily Sharpe: ({lo:.2f}, {hi:.2f}).")
    open("data/09_results/metrics_canonical.md", "w", encoding="utf-8").write("\n".join(M) + "\n")
    print("wrote data/09_results/metrics_canonical.csv + .md")
    print(f"\nMeans CR0: Ours {o['cr_0'].mean()*100:+.1f}%  No-mem {nm['cr_0'].mean()*100:+.1f}%  "
          f"B&H {bh['cr_0'].mean()*100:+.1f}%  | no-mem wins {nm_wins}/5")
    print("Per-ticker CR0 (Ours / No-mem / B&H):")
    for t in TICKERS:
        oo = o[o.ticker == t]['cr_0'].values
        nn = nm[nm.ticker == t]['cr_0'].values
        bb = bh[bh.ticker == t]['cr_0'].values
        print(f"  {t}: {oo[0]*100:+6.1f}% / {(nn[0]*100 if len(nn) else float('nan')):+6.1f}% / {bb[0]*100:+6.1f}%")
