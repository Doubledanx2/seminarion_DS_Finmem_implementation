"""Metrics v2 (work-plan step 12; extends 07-metrics.py ideas).

Primary position accounting (A4.4): position_t = direction_t (in {-1,0,1}; long-only
runs clamp at 0 via cumulative holdings logged separately by portfolio.py).
Daily strategy return: r_t = position_t * log(P_{t+1}/P_t) - cost_t, where
cost_t = (bps/1e4) * |position_t - position_{t-1}| (charged on position changes).

Reports (per ticker and portfolio):
  - Cumulative return, Sharpe (annualized, rf=0), Max Drawdown, Ann. Vol
    each WITH and WITHOUT costs (base 10 bps) + 0-50 bps sweep with break-even
    vs Buy & Hold (Sin 5)
  - Wilcoxon signed-rank vs B&H and vs no-memory (pre-declared comparisons only)
  - Moving-block bootstrap 95% CI on Sharpe (Sin 6)
  - Top-5 winning/losing days' contribution + median vs mean daily return (Sin 6)
  - Per-month returns (regime visibility)
  - Guardrail failure rate per model (A1 metric, from validation_events.jsonl)
"""
import os
import json
import numpy as np
import pandas as pd
from scipy import stats

TRADING_DAYS = 252


def strategy_returns(directions: pd.Series, prices: pd.Series, cost_bps: float = 0.0) -> pd.Series:
    """directions indexed by date (decision made on day t, applied to t->t+1 move)."""
    px = prices.reindex(directions.index).astype(float)
    log_fwd = np.log(px.shift(-1) / px)
    pos = directions.astype(float)
    turnover = (pos - pos.shift(1).fillna(0.0)).abs()
    cost = cost_bps / 1e4 * turnover
    return (pos * log_fwd - cost).dropna()


def buy_and_hold_returns(prices: pd.Series) -> pd.Series:
    px = prices.astype(float)
    return np.log(px.shift(-1) / px).dropna()


def core_metrics(r: pd.Series) -> dict:
    cum = float(np.exp(r.sum()) - 1)
    vol = float(r.std(ddof=1) * np.sqrt(TRADING_DAYS))
    sharpe = float(r.mean() / r.std(ddof=1) * np.sqrt(TRADING_DAYS)) if r.std(ddof=1) > 0 else np.nan
    eq = np.exp(r.cumsum())
    mdd = float((eq / eq.cummax() - 1).min())
    return {"cum_return": cum, "sharpe": sharpe, "max_drawdown": mdd, "ann_vol": vol,
            "mean_daily": float(r.mean()), "median_daily": float(r.median()), "n_days": len(r)}


def cost_sweep(directions: pd.Series, prices: pd.Series,
               grid_bps=(0, 5, 10, 20, 30, 40, 50)) -> pd.DataFrame:
    bh = core_metrics(buy_and_hold_returns(prices))["cum_return"]
    rows = []
    for bps in grid_bps:
        m = core_metrics(strategy_returns(directions, prices, bps))
        rows.append({"cost_bps": bps, **m, "edge_vs_bh": m["cum_return"] - bh})
    return pd.DataFrame(rows)


def break_even_bps(directions: pd.Series, prices: pd.Series, hi: float = 200.0) -> float:
    """Smallest cost (bps) at which the strategy's cumulative return drops to B&H's."""
    bh = core_metrics(buy_and_hold_returns(prices))["cum_return"]
    lo_v = core_metrics(strategy_returns(directions, prices, 0.0))["cum_return"] - bh
    if lo_v <= 0:
        return 0.0  # no edge even frictionless
    lo = 0.0
    for _ in range(40):
        mid = (lo + hi) / 2
        v = core_metrics(strategy_returns(directions, prices, mid))["cum_return"] - bh
        lo, hi = (mid, hi) if v > 0 else (lo, mid)
    return round((lo + hi) / 2, 1)


def wilcoxon_vs(r_a: pd.Series, r_b: pd.Series) -> dict:
    a, b = r_a.align(r_b, join="inner")
    d = a - b
    d = d[d != 0]
    if len(d) < 10:
        return {"n": len(d), "p_value": np.nan}
    stat, p = stats.wilcoxon(d)
    return {"n": len(d), "statistic": float(stat), "p_value": float(p)}


def block_bootstrap_sharpe_ci(r: pd.Series, block: int = 10, n_boot: int = 5000,
                              seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    x = r.to_numpy()
    n = len(x)
    sharpes = np.empty(n_boot)
    n_blocks = int(np.ceil(n / block))
    for i in range(n_boot):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        sample = np.concatenate([x[s:s + block] for s in starts])[:n]
        sd = sample.std(ddof=1)
        sharpes[i] = sample.mean() / sd * np.sqrt(TRADING_DAYS) if sd > 0 else np.nan
    lo, hi = np.nanpercentile(sharpes, [2.5, 97.5])
    return {"sharpe_ci_95": (float(lo), float(hi)), "block": block, "n_boot": n_boot}


def top5_contribution(r: pd.Series) -> dict:
    total = r.sum()
    top5 = r.nlargest(5)
    bot5 = r.nsmallest(5)
    return {
        "top5_days": {str(k): float(v) for k, v in top5.items()},
        "bottom5_days": {str(k): float(v) for k, v in bot5.items()},
        "top5_share_of_logreturn": float(top5.sum() / total) if total != 0 else np.nan,
    }


def per_month_returns(r: pd.Series) -> pd.Series:
    idx = pd.to_datetime(pd.Index(r.index))
    return np.exp(r.groupby(idx.to_period("M")).sum()) - 1


def guardrail_failure_rate(events_path=os.path.join("data", "04_model_output_log",
                                                    "validation_events.jsonl"),
                           total_calls: int = None) -> dict:
    if not os.path.exists(events_path):
        return {"reasks": 0, "fallbacks": 0}
    reasks = fallbacks = 0
    with open(events_path, encoding="utf-8") as f:
        for line in f:
            ev = json.loads(line)
            reasks += ev["event"] == "reask"
            fallbacks += ev["event"] == "fallback"
    out = {"reasks": reasks, "fallbacks": fallbacks}
    if total_calls:
        out["reask_rate"] = reasks / total_calls
        out["hold_fallback_rate"] = fallbacks / total_calls
    return out


def full_report(directions: pd.Series, prices: pd.Series, label: str,
                base_cost_bps: float = 10.0) -> dict:
    """One ticker, all Sin-5/Sin-6 numbers. directions: date-indexed {-1,0,1}."""
    r0 = strategy_returns(directions, prices, 0.0)
    rc = strategy_returns(directions, prices, base_cost_bps)
    bh = buy_and_hold_returns(prices)
    return {
        "label": label,
        "no_cost": core_metrics(r0),
        f"cost_{int(base_cost_bps)}bps": core_metrics(rc),
        "buy_and_hold": core_metrics(bh),
        "break_even_bps_vs_bh": break_even_bps(directions, prices),
        "wilcoxon_vs_bh_no_cost": wilcoxon_vs(r0, bh.reindex(r0.index)),
        "bootstrap": block_bootstrap_sharpe_ci(rc),
        "outliers": top5_contribution(rc),
        "per_month": {str(k): float(v) for k, v in per_month_returns(rc).items()},
    }
