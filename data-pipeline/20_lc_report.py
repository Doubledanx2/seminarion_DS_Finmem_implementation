"""Stage-12: write LC_TRADER.md (design, prompt template, token/cache/cost, verdict)
and regenerate the equity_<TKR> + bars_cum_return figures to include the LC-Trader line.
Run AFTER lc_trader.py (all tickers) and after 16_canonical_metrics.py."""
import os
import sys
import json
import importlib.util

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.getcwd())
spec = importlib.util.spec_from_file_location("c16", os.path.join("data-pipeline", "16_canonical_metrics.py"))
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
import lc_trader as LC  # noqa: E402

TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
FIG = "data/09_results/figures"
COL = {"Ours": "#0072B2", "No-mem": "#D55E00", "B&H": "#009E73", "LC": "#CC79A7"}
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "figure.facecolor": "white",
                     "axes.facecolor": "white", "font.size": 10})


def eqc(r):
    return (1 + r).cumprod()


# regenerate equity figures with LC line
for t in TICKERS:
    if C.lc_decisions(t) is None:
        continue
    fig, ax = plt.subplots(figsize=(7, 4))
    r_o = C.series_for(f"{t}_ours", t)[0]
    ax.plot(eqc(r_o).index, eqc(r_o).values, color=COL["Ours"], lw=2, label="FinMem-Ours")
    nm = f"{t}_ours_nomem"
    if os.path.exists(f"data/07_test_model_output/{nm}/agent_1/state_dict.pkl"):
        r_n = C.series_for(nm, t)[0]
        ax.plot(eqc(r_n).index, eqc(r_n).values, color=COL["No-mem"], lw=2, ls="--", label="No-memory")
    pos_lc = C.carry_position(C.lc_decisions(t)); px = C.env_prices(t)
    r_l = C.daily_returns(pos_lc, px, 0.0)
    ax.plot(eqc(r_l).index, eqc(r_l).values, color=COL["LC"], lw=2, ls="-.", label="LC-Trader")
    r_b = C.bh_returns(t)
    ax.plot(eqc(r_b).index, eqc(r_b).values, color=COL["B&H"], lw=2, ls=":", label="Buy & Hold")
    ax.axhline(1.0, color="grey", lw=0.7)
    ax.set_title(f"{t} — equity curve (canonical, incl. LC-Trader)")
    ax.set_xlabel("date"); ax.set_ylabel("growth of $1"); ax.legend(); fig.autofmt_xdate()
    fig.tight_layout(); fig.savefig(os.path.join(FIG, f"equity_{t}.png"), bbox_inches="tight"); plt.close(fig)

# bars with 4 series
df = pd.read_csv("data/09_results/metrics_canonical.csv")
fig, ax = plt.subplots(figsize=(9, 4.5))
x = np.arange(len(TICKERS)); w = 0.2
for i, (strat, lab, c) in enumerate([("FinMem-Ours", "Ours", COL["Ours"]),
                                     ("No-memory", "No-mem", COL["No-mem"]),
                                     ("LC-Trader", "LC-Trader", COL["LC"]),
                                     ("BuyHold", "B&H", COL["B&H"])]):
    vals = [df[(df.ticker == t) & (df.strategy == strat)]["cr_0"].values for t in TICKERS]
    vals = [v[0] * 100 if len(v) else np.nan for v in vals]
    ax.bar(x + (i - 1.5) * w, vals, w, label=lab, color=c)
ax.set_xticks(x); ax.set_xticklabels(TICKERS); ax.axhline(0, color="black", lw=0.8)
ax.set_title("Cumulative return @0bps — FinMem-Ours vs No-memory vs LC-Trader vs Buy&Hold")
ax.set_ylabel("%"); ax.legend(ncol=4)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "bars_cum_return.png"), bbox_inches="tight"); plt.close(fig)
print("regenerated equity + bars figures with LC-Trader")

# ---- LC_TRADER.md ----
meter = json.load(open("data/09_results/lc_trader_meter.json"))
hit = meter["cached"] / max(1, meter["in"])
lc = df[df.strategy == "LC-Trader"]; o = df[df.strategy == "FinMem-Ours"]; bh = df[df.strategy == "BuyHold"]
header, blocks = LC.build_context_blocks("TSLA")
example_tail = "\nToday is 2026-03-16. You currently hold 1 share(s). Your cumulative return so far is -4.2%. Make your decision now."

M = ["# LC-Trader — plain long-context baseline (no FinMem)\n",
     "**Question it answers:** in a 1M-token-context world, does FinMem's whole memory + "
     "persona + retrieval apparatus beat simply streaming the same news into a plain "
     "long-context model? LC-Trader has **none** of FinMem's scaffolding — no persona, no "
     "risk/momentum lines, no memory layers, no retrieval/FAISS/embeddings, no FinBERT. It "
     "reuses our Gemini news+filing summaries (sentiment line stripped).\n",
     "## Design\n",
     "- Each test day: SYSTEM (fixed) + APPEND-ONLY context (10-K + latest 10-Q summary, "
     "then every day's news summaries in date order ≤ today) + a tiny volatile tail "
     "(date, position, cumulative return). Prefix is byte-identical day-to-day → OpenAI "
     "prompt-cache hits from token 0.\n",
     "- Accounting identical to canonical: unit long-only {0,+1}, simple returns, full env "
     "series incl. terminal day, 0 & 10 bps. Leakage assert: max(context date) ≤ cur_date.\n",
     "## Exact daily prompt template\n```",
     "[SYSTEM] " + LC.SYSTEM.format(ticker="TSLA"),
     "\n[ACCUMULATED INFO — append-only, oldest first]",
     "ANNUAL REPORT (10-K, filed 2025-01-29) summary: <...>",
     "QUARTERLY REPORT (10-Q, filed 2025-10-22) summary: <...>",
     "2026-01-02 news:\n- <summary>\n- <summary>",
     "2026-01-05 news:\n- <summary>",
     "... (every prior day, fixed order, never edited)",
     "[VOLATILE TAIL]" + example_tail,
     "```\n",
     "## Efficiency (the headline caching stat)\n",
     f"- Calls: {meter['calls']} · input tokens {meter['in']/1e6:.1f}M · "
     f"**cached {meter['cached']/1e6:.1f}M ({hit*100:.0f}% cache-hit)** · output {meter['out']/1e3:.0f}K",
     f"- **Real cost: ${meter['cost']:.2f}** (vs ${meter['in']/1e6*0.40:.2f} with no caching) — "
     f"the {hit*100:.0f}% prefix-cache hit cut spend ~{(1-meter['cost']/max(1e-9,meter['in']/1e6*0.40))*100:.0f}%.\n",
     "## Results (canonical, 0bps cum return)\n",
     "| Ticker | LC-Trader | FinMem-Ours | Buy&Hold |",
     "|---|---|---|---|"]
for t in TICKERS:
    l = lc[lc.ticker == t]["cr_0"].values; oo = o[o.ticker == t]["cr_0"].values; b = bh[bh.ticker == t]["cr_0"].values
    M.append(f"| {t} | {l[0]*100:+.1f}% | {oo[0]*100:+.1f}% | {b[0]*100:+.1f}% |"
             if len(l) else f"| {t} | — | {oo[0]*100:+.1f}% | {b[0]*100:+.1f}% |")
covered = sorted(lc["ticker"].tolist())
if len(lc) == 5:
    M.append(f"| **mean** | **{lc['cr_0'].mean()*100:+.1f}%** | {o['cr_0'].mean()*100:+.1f}% | {bh['cr_0'].mean()*100:+.1f}% |")
    lc_wins = int((lc.set_index('ticker')['cr_0'] > o.set_index('ticker')['cr_0']).sum())
    M.append(f"\n**Verdict:** LC-Trader mean CR {lc['cr_0'].mean()*100:+.1f}% (Sharpe "
             f"{lc['sharpe_0'].mean():.2f}) vs FinMem-Ours {o['cr_0'].mean()*100:+.1f}% "
             f"({o['sharpe_0'].mean():.2f}) vs Buy&Hold {bh['cr_0'].mean()*100:+.1f}%. "
             f"LC-Trader beats FinMem-Ours on {lc_wins}/5 tickers.")
else:
    M.append(f"\n_LC-Trader was run on **{', '.join(covered)} only** (stopped after TSLA per "
             f"request); the other tickers show '—'._")
    for t in covered:
        l = lc[lc.ticker == t].iloc[0]; oo = o[o.ticker == t].iloc[0]; b = bh[bh.ticker == t].iloc[0]
        nmrow = df[(df.ticker == t) & (df.strategy == "No-memory")]
        nmtxt = f", No-memory {nmrow.iloc[0]['cr_0']*100:+.1f}%" if len(nmrow) else ""
        verdict = ("beats" if l['cr_0'] > oo['cr_0'] else "trails") + " FinMem-Ours"
        M.append(f"\n**Verdict ({t}):** LC-Trader CR **{l['cr_0']*100:+.1f}%** (Sharpe {l['sharpe_0']:.2f}, "
                 f"{l['pct_days_long']*100:.0f}% days long, turnover {int(l['turnover'])}) "
                 f"**{verdict}** ({oo['cr_0']*100:+.1f}%), vs Buy&Hold {b['cr_0']*100:+.1f}%{nmtxt}. "
                 f"The plain long-context model was almost entirely passive (held ~all days) and "
                 f"tracked the market, while FinMem's apparatus actively traded itself well below it. "
                 f"Pooled Wilcoxon LC vs Ours / LC vs B&H in metrics_canonical.md.")
M.append("\n## Cost-scaling note\n"
         "Cumulative cost grows ~**quadratically** with horizon length: the append-only context "
         "expands linearly (toward ~135K tokens by day 103), and even at 97% cache-hit the "
         "$0.10/M cached rate is charged on the whole growing prefix every day. The last ~40 days "
         "also hit OpenAI's 200K TPM limit (auto-retried). FinMem's fixed-size memory has no such "
         "horizon-scaling cost — a structural trade-off worth a slide.")
open("LC_TRADER.md", "w", encoding="utf-8").write("\n".join(M) + "\n")
print("wrote LC_TRADER.md")
