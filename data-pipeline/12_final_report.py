"""Stage-8 step 9 / Stage-10 Part C: FINAL metrics report.
RESULTS_FINMEM_OURS.md + results_finmem_ours.csv. No API calls; regenerable.

Per ticker AND mean: CR/Sharpe/MDD with & without costs (0/10 bps + 0-50 break-even);
FinMem-Ours vs B&H vs no-memory vs (TSLA) as-shipped. Pooled + per-ticker Wilcoxon
(Ours vs B&H daily), moving-block bootstrap 95% CI on Sharpe, decision mix,
guardrail-failure rate, momentum-agreement, top-5-day share, per-month returns.
Tickers whose test isn't complete (< MIN_TEST_DAYS 2026 reflections) are skipped.
"""
import os
import sys
import json
import pickle
import importlib.util

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.getcwd())  # repo root: pickle.load needs `puppy`
TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
MIN_TEST_DAYS = 90
OUT_MD = "RESULTS_FINMEM_OURS.md"
OUT_CSV = os.path.join("data", "09_results", "results_finmem_ours.csv")

spec = importlib.util.spec_from_file_location("m7", os.path.join("data-pipeline", "07_metrics_v2.py"))
m7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m7)


def load_test(tag):
    """Returns (dirs, px, refl) keyed off the FINAL output dir, only if the test is
    complete (>= MIN_TEST_DAYS 2026 reflections). None otherwise."""
    p = os.path.join("data", "07_test_model_output", tag, "agent_1", "state_dict.pkl")
    if not os.path.exists(p):
        return None
    sd = pickle.load(open(p, "rb"))
    refl = {d: r for d, r in sd["reflection_result_series_dict"].items() if d.year == 2026}
    if len(refl) < MIN_TEST_DAYS:
        return None
    pf = sd["portfolio"]
    dirs = pd.Series({d: a for d, a in pf.action_series.items() if d.year == 2026}).sort_index()
    px = pd.Series(dict(zip(pf.date_series, pf.market_price_series)))
    px = px[[d for d in px.index if d.year == 2026]].sort_index()
    return dirs, px, refl


def guardrail_stats(symbol, mode_suffix="2026"):
    path = os.path.join("data", "04_model_output_log", "validation_events.jsonl")
    re_, fb = 0, 0
    if os.path.exists(path):
        for line in open(path, encoding="utf-8-sig"):  # tolerate BOM
            ev = json.loads(line)
            if ev["symbol"] == symbol and ev.get("run_mode", "").startswith("test") \
                    and ev["date"].startswith("2026"):
                re_ += ev["event"] == "reask"
                fb += ev["event"] != "reask"
    return re_, fb


def metrics_block(dirs, px, label, cost=10.0):
    return m7.full_report(dirs, px, label, base_cost_bps=cost)


rows, md = [], []
md.append("# RESULTS — FinMem-Ours (frozen #3, `96d724d`) · test 2026-01-02 → 2026-06-01\n")
md.append("Paper architecture + all our fixes. Train 2025-07-01→12-31. Pre-declared "
          "comparisons: FinMem-Ours vs Buy&Hold, vs no-memory ablation, vs TSLA as-shipped "
          "(exhibit). Long-only unit positions; metrics on direction×next-day log return.\n")

# collect per-ticker daily return series for pooled tests
ours_daily_pool, bh_daily_pool, nomem_daily_pool, ours_for_nomem_pool = [], [], [], []
asshipped = None
fl = os.path.join("data", "07_test_model_output", "TSLA", "first_look.pkl")
if os.path.exists(fl):
    asshipped = pickle.load(open(fl, "rb"))["report"]

for t in TICKERS:
    data = load_test(f"{t}_ours")
    if data is None:
        md.append(f"\n## {t}: TEST INCOMPLETE (<{MIN_TEST_DAYS} days) — excluded\n")
        continue
    dirs, px, refl = data
    rep = metrics_block(dirs, px, f"{t}-ours")
    nomem = load_test(f"{t}_ours_nomem")
    nm_rep = metrics_block(nomem[0], nomem[1], f"{t}-nomem") if nomem else None

    r0, r10, bh = rep["no_cost"], rep["cost_10bps"], rep["buy_and_hold"]
    ours_r = m7.strategy_returns(dirs, px, 0.0)
    bh_r = m7.buy_and_hold_returns(px).reindex(ours_r.index)
    ours_daily_pool.append(ours_r); bh_daily_pool.append(bh_r)
    if nomem:
        nm_r = m7.strategy_returns(nomem[0], nomem[1], 0.0)
        common = ours_r.index.intersection(nm_r.index)
        nomem_daily_pool.append(nm_r.reindex(common))
        ours_for_nomem_pool.append(ours_r.reindex(common))
    wil = m7.wilcoxon_vs(ours_r, bh_r)
    mix = pd.Series([r.get("investment_decision", "hold") for r in refl.values()]).value_counts().to_dict()
    re_, fb = guardrail_stats(t)
    ma = rep["momentum_agreement"]

    row = {"ticker": t,
           "ours_cr_0": r0["cum_return"], "ours_sharpe_0": r0["sharpe"],
           "ours_cr_10": r10["cum_return"], "ours_sharpe_10": r10["sharpe"], "ours_mdd_10": r10["max_drawdown"],
           "bh_cr": bh["cum_return"], "bh_sharpe": bh["sharpe"], "bh_mdd": bh["max_drawdown"],
           "nomem_cr_0": nm_rep["no_cost"]["cum_return"] if nm_rep else None,
           "nomem_sharpe_0": nm_rep["no_cost"]["sharpe"] if nm_rep else None,
           "nomem_cr_10": nm_rep["cost_10bps"]["cum_return"] if nm_rep else None,
           "break_even_bps": rep["break_even_bps_vs_bh"],
           "wilcoxon_p_vs_bh": wil["p_value"],
           "sharpe_ci_lo": rep["bootstrap"]["sharpe_ci_95"][0], "sharpe_ci_hi": rep["bootstrap"]["sharpe_ci_95"][1],
           "buy": mix.get("buy", 0), "hold": mix.get("hold", 0), "sell": mix.get("sell", 0),
           "momentum_agreement": ma["agreement_rate"], "reasks": re_, "fallbacks": fb,
           "top5_share": rep["outliers"]["top5_share_of_logreturn"]}
    rows.append(row)

    md.append(f"\n## {t}\n")
    md.append("| | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |")
    md.append("|---|---|---|---|---|")
    nmcr0 = f"{nm_rep['no_cost']['cum_return']*100:+.1f}%" if nm_rep else "—"
    nmsh0 = f"{nm_rep['no_cost']['sharpe']:.2f}" if nm_rep else "—"
    md.append(f"| Cum. return | {r0['cum_return']*100:+.1f}% | {r10['cum_return']*100:+.1f}% | {bh['cum_return']*100:+.1f}% | {nmcr0} |")
    md.append(f"| Sharpe | {r0['sharpe']:.2f} | {r10['sharpe']:.2f} | {bh['sharpe']:.2f} | {nmsh0} |")
    md.append(f"| Max drawdown | {r0['max_drawdown']*100:.1f}% | {r10['max_drawdown']*100:.1f}% | {bh['max_drawdown']*100:.1f}% | |")
    md.append(f"\nBreak-even vs B&H: **{row['break_even_bps']} bps** · Wilcoxon (Ours vs B&H daily) "
              f"p={wil['p_value']:.3f} (n={wil['n']}) · bootstrap Sharpe 95% CI "
              f"({row['sharpe_ci_lo']:.2f}, {row['sharpe_ci_hi']:.2f})")
    md.append(f"Decisions: {row['buy']} buy / {row['hold']} hold / {row['sell']} sell · "
              f"momentum-agreement {ma['agreement_rate']*100:.0f}% (n={ma['n_decided']}) · "
              f"guardrails: {re_} re-asks / {fb} fallbacks · top-5-day share {row['top5_share']:.2f}")
    md.append("Per-month (10bps): " + ", ".join(f"{k} {v*100:+.1f}%" for k, v in rep["per_month"].items()))

# ---------- mean row ----------
if rows:
    df = pd.DataFrame(rows)
    md.append("\n## Mean across completed tickers\n")
    md.append("| metric | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |")
    md.append("|---|---|---|---|---|")
    def mean(col):
        v = pd.to_numeric(df[col], errors="coerce").dropna()
        return v.mean() if len(v) else float("nan")
    md.append(f"| Cum. return | {mean('ours_cr_0')*100:+.1f}% | {mean('ours_cr_10')*100:+.1f}% | {mean('bh_cr')*100:+.1f}% | {mean('nomem_cr_0')*100:+.1f}% |")
    md.append(f"| Sharpe | {mean('ours_sharpe_0'):.2f} | {mean('ours_sharpe_10'):.2f} | {mean('bh_sharpe'):.2f} | {mean('nomem_sharpe_0'):.2f} |")
    md.append(f"| Mean break-even {mean('break_even_bps'):.0f} bps · mean momentum-agreement "
              f"{mean('momentum_agreement')*100:.0f}% · total guardrail re-asks {int(df['reasks'].sum())}, "
              f"fallbacks {int(df['fallbacks'].sum())} |")

    # ---------- HEADLINE: memory effect ----------
    nm_mean = pd.to_numeric(df["nomem_cr_0"], errors="coerce").dropna()
    if len(nm_mean) == len(df):
        n_hurt = int(((df["nomem_cr_0"] > df["ours_cr_0"]) ).sum())
        md.append(f"\n### Memory effect (headline)\n")
        md.append(f"No-memory ablation mean CR **{nm_mean.mean()*100:+.1f}%** vs FinMem-Ours "
                  f"**{mean('ours_cr_0')*100:+.1f}%** vs B&H {mean('bh_cr')*100:+.1f}% (0bps). "
                  f"Removing memory HELPED on {n_hurt}/5 tickers — the layered-memory module did "
                  f"not add value on leakage-free out-of-sample data (and hurt on average). "
                  f"This is the central negative result.")

    # ---------- pooled Wilcoxon ----------
    if ours_daily_pool:
        a = pd.concat(ours_daily_pool).reset_index(drop=True)
        b = pd.concat(bh_daily_pool).reset_index(drop=True)
        d = (a - b).dropna(); d = d[d != 0]
        if len(d) >= 10:
            stat, p = stats.wilcoxon(d)
            md.append(f"\n**Pooled Wilcoxon** (all tickers, FinMem-Ours vs B&H daily, n={len(d)}): "
                      f"p={p:.4f}; median daily edge {d.median()*1e4:+.1f} bps.")
    if nomem_daily_pool:
        a = pd.concat(ours_for_nomem_pool).reset_index(drop=True)
        b = pd.concat(nomem_daily_pool).reset_index(drop=True)
        d = (a - b).dropna(); d = d[d != 0]
        if len(d) >= 10:
            stat, p = stats.wilcoxon(d)
            md.append(f"**Pooled Wilcoxon** (FinMem-Ours vs no-memory daily, n={len(d)}): "
                      f"p={p:.4f}; median daily memory effect {d.median()*1e4:+.1f} bps "
                      f"(negative ⇒ memory hurt).")

# ---------- TSLA as-shipped exhibit ----------
if asshipped:
    md.append("\n## Exhibit: TSLA as-shipped (frozen `f170a92`) — before/after our fixes\n")
    md.append(f"As-shipped TSLA test: CR {asshipped['no_cost']['cum_return']*100:+.1f}% (0bps), "
              f"Sharpe {asshipped['no_cost']['sharpe']:.2f}, break-even {asshipped['break_even_bps_vs_bh']} bps, "
              f"100% momentum agreement (pure momentum follower; deep memory was a 3-day revolving door — "
              f"see DEEP_LAYER_TRACE.md). FinMem-Ours TSLA row above is the after.")

# ---------- portfolio layer ----------
pl_res = os.path.join("data", "09_results", "portfolio_layer_result.json")
if os.path.exists(pl_res):
    pr = json.load(open(pl_res, encoding="utf-8-sig"))
    md.append("\n## Portfolio layer (our extension)\n")
    md.append(f"Allocator portfolio CR {pr['portfolio_cum_return']*100:+.1f}% vs equal-weight B&H "
              f"{pr['equal_weight_bh_cum_return']*100:+.1f}% over {len(pr['days'])} test days.")

md.append(f"\n---\n_Generated from checkpoints by 12_final_report.py · "
          f"{len(rows)}/5 tickers complete · see DEEP_DIVE.md for decision/memory analysis._")

os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")
print(f"wrote {OUT_MD} ({len(rows)}/5 tickers) + {OUT_CSV}")
