"""Stage-8/10/11: FINAL narrative report -> RESULTS_FINMEM_OURS.md.
Numbers come from the AUDITED canonical engine (16_canonical_metrics): carry-forward
unit-long-only positions, simple compounded returns, full env price series. This
SUPERSEDES the pre-audit RESULTS that used raw decisions as the position (hold=flat,
sell=SHORT) + log returns and inflated every cell. No API calls.
"""
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

spec = importlib.util.spec_from_file_location("c16", os.path.join("data-pipeline", "16_canonical_metrics.py"))
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def decision_mix(tag):
    sd = pickle.load(open(f"data/07_test_model_output/{tag}/agent_1/state_dict.pkl", "rb"))
    s = pd.Series([r.get("investment_decision", "hold")
                   for d, r in sd["reflection_result_series_dict"].items() if d.year == 2026])
    return s.value_counts().to_dict()


def momentum_agreement(tag, ticker):
    sd = pickle.load(open(f"data/07_test_model_output/{tag}/agent_1/state_dict.pkl", "rb"))
    dec = pd.Series({d: r.get("investment_decision", "hold")
                     for d, r in sd["reflection_result_series_dict"].items() if d.year == 2026}).sort_index()
    px = C.env_prices(ticker).reindex(dec.index)
    mom = np.sign(px - px.shift(3))
    dnum = dec.map({"buy": 1, "sell": -1, "hold": 0})
    decided = dnum[dnum != 0].index.intersection(mom.dropna().index)
    if len(decided) == 0:
        return float("nan"), 0
    agree = (dnum.loc[decided] == mom.loc[decided]).mean()
    return float(agree), len(decided)


def guardrails(symbol):
    path = "data/04_model_output_log/validation_events.jsonl"
    re_, fb = 0, 0
    if os.path.exists(path):
        for line in open(path, encoding="utf-8-sig"):
            ev = json.loads(line)
            if ev["symbol"] == symbol and ev.get("run_mode", "").startswith("test") and ev["date"].startswith("2026"):
                re_ += ev["event"] == "reask"; fb += ev["event"] != "reask"
    return re_, fb


def per_month(tag, ticker):
    r = C.series_for(tag, ticker, 10.0)[0]
    idx = pd.to_datetime(pd.Index(r.index))
    return (np.exp(np.log1p(r).groupby(idx.to_period("M")).sum()) - 1)


md = ["# RESULTS — FinMem-Ours (audited, canonical) · test 2026-01-02 → 2026-06-01\n",
      "> ⚠️ **Corrected metrics (Stage-11 audit).** Earlier builds of this file used raw "
      "decisions as the position (hold=flat, sell=SHORT) + log returns, which created "
      "phantom short profits and inflated every cell (e.g. NFLX no-mem read +57% vs the "
      "true +20%, NFLX-Ours +19% vs the true +3.8%). All numbers below use the canonical "
      "convention: **carry-forward unit long-only {0,+1} × simple next-day return, "
      "compounded, on the full env price series.** Full table: "
      "`data/09_results/metrics_canonical.{md,csv}`; reconciliation: `15_reconcile.py`.\n"]

# build canonical rows
rows = []
ours_pool, nm_pool, bh_pool, ours_for_nm = [], [], [], []
for t in TICKERS:
    ro, r_o = C.row_for("FinMem-Ours", f"{t}_ours", t); rows.append(ro); ours_pool.append(r_o)
    bh = C.bh_row(t); rows.append(bh[0]); bh_pool.append(bh[1])
    nm_tag = f"{t}_ours_nomem"
    rn = None
    if os.path.exists(f"data/07_test_model_output/{nm_tag}/agent_1/state_dict.pkl"):
        rn, r_n = C.row_for("No-memory", nm_tag, t); rows.append(rn)
        common = r_o.index.intersection(r_n.index)
        nm_pool.append(r_n.reindex(common)); ours_for_nm.append(r_o.reindex(common))
    mix = decision_mix(f"{t}_ours"); ma, man = momentum_agreement(f"{t}_ours", t); re_, fb = guardrails(t)
    o = ro; b = bh[0]
    md.append(f"\n## {t}\n")
    md.append("| | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |")
    md.append("|---|---|---|---|---|")
    nmcr = f"{rn['cr_0']*100:+.1f}%" if rn else "—"
    nmsh = f"{rn['sharpe_0']:.2f}" if rn else "—"
    md.append(f"| Cum. return | {o['cr_0']*100:+.1f}% | {o['cr_10']*100:+.1f}% | {b['cr_0']*100:+.1f}% | {nmcr} |")
    md.append(f"| Sharpe | {o['sharpe_0']:.2f} | {o['sharpe_10']:.2f} | {b['sharpe_0']:.2f} | {nmsh} |")
    md.append(f"| Sortino | {o['sortino_0']:.2f} | | {b['sortino_0']:.2f} | |")
    md.append(f"| Max drawdown | {o['mdd_0']*100:.1f}% | {o['mdd_10']*100:.1f}% | {b['mdd_0']*100:.1f}% | |")
    md.append(f"\nAnn.vol {o['ann_vol_0']*100:.0f}% · alpha(ann) {o['alpha_ann_0']*100:+.1f}% · beta {o['beta_vs_bh_0']:.2f} "
              f"· turnover {o['turnover']} · {o['pct_days_long']*100:.0f}% days long")
    md.append(f"Decisions: {mix.get('buy',0)} buy / {mix.get('hold',0)} hold / {mix.get('sell',0)} sell · "
              f"momentum-agreement {ma*100:.0f}% (n={man}) · guardrails: {re_} re-asks / {fb} fallbacks")
    pm = per_month(f"{t}_ours", t)
    md.append("Per-month (10bps): " + ", ".join(f"{k} {v*100:+.1f}%" for k, v in pm.items()))

df = pd.DataFrame(rows)
o = df[df.strategy == "FinMem-Ours"]; nm = df[df.strategy == "No-memory"]; bh = df[df.strategy == "BuyHold"]
md.append("\n## Mean across 5 tickers (0bps)\n")
md.append("| | FinMem-Ours | Buy&Hold | No-memory |")
md.append("|---|---|---|---|")
md.append(f"| Cum. return | {o['cr_0'].mean()*100:+.1f}% | {bh['cr_0'].mean()*100:+.1f}% | {nm['cr_0'].mean()*100:+.1f}% |")
md.append(f"| Sharpe | {o['sharpe_0'].mean():.2f} | {bh['sharpe_0'].mean():.2f} | {nm['sharpe_0'].mean():.2f} |")

from scipy import stats
def pooled(a_list, b_list):
    a = pd.concat(a_list).reset_index(drop=True); b = pd.concat(b_list).reset_index(drop=True)
    d = (a - b).dropna(); d = d[d != 0]
    if len(d) < 10:
        return None
    p = float(stats.wilcoxon(d)[1])
    return {"n": len(d), "p": p, "median": float(d.median())}

w_bh = pooled(ours_pool, bh_pool)
w_nm = pooled(ours_for_nm, nm_pool) if nm_pool else None
nm_wins = int((nm.set_index('ticker')['cr_0'] > o.set_index('ticker')['cr_0']).sum()) if len(nm) == 5 else None
md.append("\n## Memory effect (audited)\n")
md.append(f"FinMem-Ours mean CR **{o['cr_0'].mean()*100:+.1f}%** · Buy&Hold **{bh['cr_0'].mean()*100:+.1f}%** · "
          f"No-memory **{nm['cr_0'].mean()*100:+.1f}%** (0bps). FinMem-Ours UNDERPERFORMS Buy&Hold on the mean; "
          f"the no-memory ablation is the best of the three and beats full FinMem-Ours on "
          f"**{nm_wins}/5** tickers. The layered memory did not add value out-of-sample "
          f"(direction unchanged from the pre-audit conclusion, magnitude much smaller).")
if w_bh:
    md.append(f"\n**Pooled Wilcoxon** Ours vs B&H (n={w_bh['n']}): p={w_bh['p']:.4f}, median daily edge {w_bh['median']*1e4:+.1f} bps.")
if w_nm:
    md.append(f"**Pooled Wilcoxon** Ours vs No-memory (n={w_nm['n']}): p={w_nm['p']:.4f}, "
              f"median daily memory effect {w_nm['median']*1e4:+.1f} bps (neg ⇒ memory hurt).")
asr = df[df.strategy == "As-shipped"]
if len(asr) == 0:
    arow, _ = C.row_for("As-shipped", "TSLA", "TSLA", as_shipped=True); asr = pd.DataFrame([arow])
ar = asr.iloc[0]
md.append("\n## Exhibit: TSLA as-shipped (frozen `f170a92`) — canonical\n")
md.append(f"As-shipped TSLA: CR {ar['cr_0']*100:+.1f}% (0bps), Sharpe {ar['sharpe_0']:.2f} "
          f"vs FinMem-Ours TSLA CR {o[o.ticker=='TSLA']['cr_0'].values[0]*100:+.1f}%. Both lose to "
          f"B&H ({bh[bh.ticker=='TSLA']['cr_0'].values[0]*100:+.1f}%); as-shipped was a 100%-momentum "
          f"follower with a 3-day-revolving deep layer (F1/F2, DEEP_LAYER_TRACE.md).")
pl_res = "data/09_results/portfolio_layer_result.json"
if os.path.exists(pl_res):
    pr = json.load(open(pl_res, encoding="utf-8-sig"))
    md.append(f"\n## Portfolio layer (our extension)\n_(reported as logged; recompute under the "
              f"canonical convention is in the deck figures.)_ Allocator CR "
              f"{pr['portfolio_cum_return']*100:+.1f}% vs equal-weight B&H {pr['equal_weight_bh_cum_return']*100:+.1f}%.")
md.append(f"\n---\n_Canonical numbers from 16_canonical_metrics.py · full table "
          f"data/09_results/metrics_canonical.md · figures data/09_results/figures/ · "
          f"see DEEP_DIVE.md + deck_excerpts.md._")

open(OUT_MD, "w", encoding="utf-8").write("\n".join(md) + "\n")
print(f"wrote {OUT_MD} (canonical)")
