"""Stage-8 step 9: FINAL metrics report -> RESULTS_FINMEM_OURS.md + CSV.
No API calls; regenerable any time from checkpoints. Skips tickers whose test
hasn't finished (partial grid beats nothing)."""
import os
import sys
import json
import pickle
import importlib.util

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
OUT_MD = "RESULTS_FINMEM_OURS.md"
OUT_CSV = os.path.join("data", "09_results", "results_finmem_ours.csv")

spec = importlib.util.spec_from_file_location("m7", os.path.join("data-pipeline", "07_metrics_v2.py"))
m7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m7)


def load_test(tag):
    p = os.path.join("data", "07_test_model_output", tag, "agent_1", "state_dict.pkl")
    if not os.path.exists(p):
        return None
    sd = pickle.load(open(p, "rb"))
    pf = sd["portfolio"]
    dirs = pd.Series({d: a for d, a in pf.action_series.items() if d.year == 2026}).sort_index()
    px = pd.Series(dict(zip(pf.date_series, pf.market_price_series)))
    px = px[[d for d in px.index if d.year == 2026]].sort_index()
    refl = {d: r for d, r in sd["reflection_result_series_dict"].items() if d.year == 2026}
    return dirs, px, refl


def guardrail_stats(symbol):
    path = os.path.join("data", "04_model_output_log", "validation_events.jsonl")
    re_, fb = 0, 0
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            ev = json.loads(line)
            if ev["symbol"] == symbol and ev["date"].startswith("2026"):
                re_ += ev["event"] == "reask"
                fb += ev["event"] != "reask"
    return re_, fb


rows, md = [], []
md.append("# RESULTS — FinMem-Ours (frozen #3) · test 2026-01-02 → 2026-06-01\n")
md.append("Main config: paper architecture + our fixes (see IMPLEMENTATION_LOG). "
          "Pre-declared comparisons only; exploratory items labeled.\n")

for t in TICKERS:
    data = load_test(f"{t}_ours")
    if data is None:
        md.append(f"\n## {t}: TEST NOT COMPLETE — excluded from this build of the report\n")
        continue
    dirs, px, refl = data
    rep = m7.full_report(dirs, px, f"{t}-ours", base_cost_bps=10)
    mix = pd.Series([r.get("investment_decision", "hold") for r in refl.values()]).value_counts().to_dict()
    re_, fb = guardrail_stats(t)
    ma = rep["momentum_agreement"]
    row = {"ticker": t,
           "cr_0bps": rep["no_cost"]["cum_return"], "sharpe_0bps": rep["no_cost"]["sharpe"],
           "cr_10bps": rep["cost_10bps"]["cum_return"], "sharpe_10bps": rep["cost_10bps"]["sharpe"],
           "mdd_10bps": rep["cost_10bps"]["max_drawdown"],
           "bh_cr": rep["buy_and_hold"]["cum_return"], "bh_sharpe": rep["buy_and_hold"]["sharpe"],
           "break_even_bps": rep["break_even_bps_vs_bh"],
           "wilcoxon_p": rep["wilcoxon_vs_bh_no_cost"]["p_value"],
           "sharpe_ci_lo": rep["bootstrap"]["sharpe_ci_95"][0],
           "sharpe_ci_hi": rep["bootstrap"]["sharpe_ci_95"][1],
           "buy": mix.get("buy", 0), "hold": mix.get("hold", 0), "sell": mix.get("sell", 0),
           "momentum_agreement": ma["agreement_rate"], "reasks": re_, "fallbacks": fb,
           "top5_share": rep["outliers"]["top5_share_of_logreturn"]}
    rows.append(row)
    md.append(f"\n## {t}\n")
    md.append(f"| metric | FinMem-Ours (0bps) | FinMem-Ours (10bps) | Buy&Hold |\n|---|---|---|---|")
    md.append(f"| Cum. return | {row['cr_0bps']*100:+.1f}% | {row['cr_10bps']*100:+.1f}% | {row['bh_cr']*100:+.1f}% |")
    md.append(f"| Sharpe | {row['sharpe_0bps']:.2f} | {row['sharpe_10bps']:.2f} | {row['bh_sharpe']:.2f} |")
    md.append(f"| Max drawdown (10bps) | | {row['mdd_10bps']*100:.1f}% | |")
    md.append(f"\nBreak-even vs B&H: **{row['break_even_bps']} bps** · Wilcoxon p={row['wilcoxon_p']:.3f} · "
              f"Sharpe 95% CI ({row['sharpe_ci_lo']:.2f}, {row['sharpe_ci_hi']:.2f})")
    md.append(f"Decisions: {row['buy']} buy / {row['hold']} hold / {row['sell']} sell · "
              f"momentum agreement {row['momentum_agreement']*100:.0f}% · "
              f"guardrails: {re_} re-asks, {fb} fallbacks · top-5-day share {row['top5_share']:.2f}")
    md.append(f"Per-month: " + ", ".join(f"{k}: {v*100:+.1f}%" for k, v in rep["per_month"].items()))

# exhibits
fl = os.path.join("data", "07_test_model_output", "TSLA", "first_look.pkl")
if os.path.exists(fl):
    ex = pickle.load(open(fl, "rb"))["report"]
    md.append("\n## Exhibit: TSLA as-shipped (frozen f170a92) — before/after\n")
    md.append(f"As-shipped: CR {ex['no_cost']['cum_return']*100:+.1f}% (0bps), "
              f"Sharpe {ex['no_cost']['sharpe']:.2f}, break-even {ex['break_even_bps_vs_bh']} bps, "
              f"momentum agreement 100%.")
nm = load_test("TSLA_ours_nomem")
if nm:
    rep = m7.full_report(nm[0], nm[1], "nomem", base_cost_bps=10)
    md.append(f"\n## Ablation: TSLA no-memory (same backbone/prompt, empty retrieval)\n")
    md.append(f"CR {rep['no_cost']['cum_return']*100:+.1f}% (0bps) / "
              f"{rep['cost_10bps']['cum_return']*100:+.1f}% (10bps), "
              f"Sharpe {rep['no_cost']['sharpe']:.2f}.")
pl_res = os.path.join("data", "09_results", "portfolio_layer_result.json")
if os.path.exists(pl_res):
    pr = json.load(open(pl_res))
    md.append(f"\n## Portfolio layer (our extension)\n")
    md.append(f"Portfolio CR {pr['portfolio_cum_return']*100:+.1f}% vs equal-weight B&H "
              f"{pr['equal_weight_bh_cum_return']*100:+.1f}% over {len(pr['days'])} test days.")

os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")
print(f"wrote {OUT_MD} ({len(rows)}/5 tickers) + {OUT_CSV}")
