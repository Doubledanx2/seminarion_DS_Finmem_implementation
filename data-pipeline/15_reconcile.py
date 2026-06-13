"""Stage-11 Part A: reconcile the no-memory metric discrepancy.
Reproduces BOTH the committed (buggy) number and the independent recompute,
isolating the cause. No new runs. Reads test state_dicts + env price pickles.
"""
import os
import sys
import pickle
import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
T0, T1 = datetime.date(2026, 1, 2), datetime.date(2026, 6, 1)


def env_prices(ticker):
    """FULL test-window price series incl. the terminal day (env pickle, not the
    portfolio series which ends one day early)."""
    env = pickle.load(open(f"data/03_model_input/{ticker.lower()}.pkl", "rb"))
    days = sorted(d for d in env if d.year == 2026 and T0 <= d <= T1)
    return pd.Series({d: float(env[d]["price"][ticker]) for d in days})


def decisions(tag):
    sd = pickle.load(open(f"data/07_test_model_output/{tag}/agent_1/state_dict.pkl", "rb"))
    refl = sd["reflection_result_series_dict"]
    dec = {d: r.get("investment_decision", "hold") for d, r in refl.items() if d.year == 2026}
    return pd.Series(dec).sort_index(), sd["portfolio"]


def carry_position(dec: pd.Series) -> pd.Series:
    """Canonical: carry-forward, unit long-only. buy=enter/keep(1), sell=exit(0),
    hold=carry. Position held INTO the next day."""
    h, out = 0, {}
    for d, a in dec.items():
        if a == "buy":
            h = 1
        elif a == "sell":
            h = 0
        out[d] = h
    return pd.Series(out)


def raw_position(dec: pd.Series) -> pd.Series:
    """The BUGGY convention the committed report used: raw decision as position,
    so hold=flat, sell=SHORT(-1)."""
    return dec.map({"buy": 1, "hold": 0, "sell": -1}).astype(float)


def cum_simple(pos, px):
    """position_t * simple next-day return, compounded, on the full price series."""
    common = pos.index.intersection(px.index)
    p = pos.reindex(px.index).ffill().fillna(0)
    fwd = px.shift(-1) / px - 1.0
    r = (p * fwd).dropna()
    return float(np.prod(1 + r) - 1), r


def cum_log(pos, px):
    common = pos.index
    p = pos.reindex(px.index).ffill().fillna(0)
    fwd = np.log(px.shift(-1) / px)
    r = (p * fwd).dropna()
    return float(np.exp(r.sum()) - 1), r


if __name__ == "__main__":
    print("RECONCILIATION — no-memory cumulative return @0bps\n")
    hdr = f"{'ticker':6} {'B&H':>8} {'RAW-pos/LOG (committed)':>24} {'CARRY-pos/SIMPLE (canonical)':>30}"
    print(hdr); print("-" * len(hdr))
    for t in TICKERS:
        px = env_prices(t)
        bh = float(px.iloc[-1] / px.iloc[0] - 1)
        for tag, lab in [(f"{t}_ours_nomem", "nomem")]:
            if not os.path.exists(f"data/07_test_model_output/{tag}/agent_1/state_dict.pkl"):
                continue
            dec, pf = decisions(tag)
            raw_cum, _ = cum_log(raw_position(dec), px)
            carry_cum, _ = cum_simple(carry_position(dec), px)
            print(f"{t:6} {bh*100:+7.1f}% {raw_cum*100:+22.1f}% {carry_cum*100:+28.1f}%")
    print("\nLegend: RAW-pos/LOG = the committed report's convention "
          "(raw decision as position: hold=flat, sell=SHORT; log returns).")
    print("CARRY-pos/SIMPLE = canonical (carry-forward unit long-only; simple compounded).")
    print("\nFormula used by committed 07_metrics_v2.strategy_returns:")
    print("  pos = action_series (RAW decision +1/0/-1)   <-- BUG: not the held position")
    print("  log_fwd = log(price.shift(-1)/price)         <-- log, and on portfolio series")
    print("  daily = pos * log_fwd - cost;  cum = exp(sum(daily)) - 1")
