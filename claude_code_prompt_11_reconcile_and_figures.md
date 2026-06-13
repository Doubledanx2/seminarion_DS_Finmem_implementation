# Prompt for Claude Code — Stage 11: reconcile metrics (AUDIT) + render presentation figures

Copy below into Claude Code. Reason: an independent recompute of the no-memory results
from the test checkpoints does NOT match the numbers in STATUS/RESULTS. We must resolve
this before it goes in a deck — this project's whole thesis is "don't trust unaudited
backtest numbers." Treat as a Sin-4/Sin-5 self-audit.

---

## ⛔ ROOT CAUSE ALREADY FOUND BY DAN — fix this first, it dominates everything

TSLA Buy&Hold in RESULTS = −0.5%. TRUE full-window B&H (2026-01-02 → 2026-06-01) =
**−5.07%**. Verified cause: the report computes returns ending at the **second-to-last
test date (2026-05-29, −0.52%)** and DROPS the final day **2026-06-01, which was a
−4.57% TSLA day**. This is the terminal-day truncation we hit once before, and it
biases EVERY cell (Ours/no-mem/B&H/as-shipped) because the agents were long into that
drop. The convention is NOT the main issue (log and simple both give ≈−5%); the
MISSING LAST DAY is.

MANDATORY FIX: every return series must be priced on the FULL env price series,
covering all trading days from the first test date through and INCLUDING the final
test date. Add a regression assertion: B&H cumulative return recomputed in the metrics
module must equal `P[last]/P[first]-1` per ticker (e.g. TSLA = −5.07%) within 1e-6.
If it doesn't, the run must fail. Re-derive every table and figure after this fix.

## Part A — reconcile the discrepancy (do FIRST, no new runs)

Independent recompute (positions carried forward; buy→long, sell→flat only if holding,
hold→carry; daily strat return = position × next-day simple return; compound) gives:

| ticker | B&H | Ours @0bps | no-mem @0bps (recomputed) | STATUS/RESULTS claimed no-mem |
|---|---|---|---|---|
| NFLX | −5.6% | +3.8% | **+19.8%** | +57% (??) |
| AMZN | +15.3% | +15.5% | **+24.5%** | +47% (??) |
| TSLA | −5.1% | −23.1% | −5.5% | −11% |
| MSFT | −2.2% | −3.9% | −6.0% | — |
| COIN | −22.8% | −18.5% | −24.2% | — |

1. Find why `12_final_report.py` (or metrics-v2) produces different no-memory numbers.
   Likely suspects: (a) position accounting differs (e.g. treating raw ±1 with shorting
   vs our unit long-only clamp), (b) log vs simple returns, (c) terminal-day handling
   (we hit this before — portfolio series ends one day early), (d) summing daily
   returns instead of compounding, (e) reading the wrong run dir. Print the exact
   formula the script uses, line by line, next to the recompute.
2. **Adopt ONE canonical return convention** and document it in RESULTS header:
   simple daily returns, position × next-day move, compounded, priced on the FULL env
   series incl. terminal day, unit long-only. Recompute EVERY cell (Ours, no-mem, B&H,
   as-shipped) the same way. Anything that changes from the committed RESULTS → log it
   as a corrected-metric finding (good, honest).
3. Re-run pooled + per-ticker Wilcoxon and bootstrap Sharpe CI on the canonical series.

## Part B — full metric set per ticker + mean (canonical convention)

For Ours / no-mem / B&H / (TSLA also as-shipped), at 0 and 10 bps:
cumulative return, annualized return, **annualized volatility (std)**, **Sharpe**,
**Sortino**, **max drawdown**, **alpha & beta vs its own B&H** (daily OLS), turnover
(position changes), % days long. One tidy CSV `data/09_results/metrics_canonical.csv`
+ a markdown table. This is the table the deck will quote — must be self-consistent.

## Part C — render figures as PNG (matplotlib, headless, no API) → `data/09_results/figures/`

1. `equity_<TKR>.png` ×5: Ours vs no-mem vs B&H equity curves over the test window.
2. `bars_cum_return.png`: grouped bars, 5 tickers × {Ours, no-mem, B&H} @0bps.
3. `bars_sharpe.png`: same grouping, Sharpe.
4. `costs_breakeven_<TKR>.png`: Ours CR vs bps (0–50) with the B&H line + break-even dot.
5. `persona_timeline_NFLX.png`: risk-seeking vs risk-averse mode by day, colored,
   with the price line overlaid (NFLX = our standout).
6. `citation_share.png`: stacked bar of memory-layer citation share per ticker
   (short/mid/long/reflection).
7. `vectordb_<TKR>.png` (NFLX + TSLA): 2-D PCA/UMAP scatter of the end-state FAISS
   vectors, colored by layer, sized by importance — a real "vector DB" visual.
8. `memory_growth_NFLX.png`: deep-layer occupancy over time (Ours retains) vs the
   as-shipped TSLA revolving-door line on the same axes (the F2 contrast).
All figures: title, axis labels, legend, colorblind-safe palette, 150 dpi, white bg.

## Part D — text excerpts file `data/09_results/deck_excerpts.md`

Pull VERBATIM, ready to paste into slides:
- 2 example FULL prompts actually sent to the model (one risk-seeking day, one
  risk-averse day) — trimmed to the structurally interesting parts, ticker+date labeled.
- 3 persona-switch reasoning quotes (the "risk-averse investor"/"risk-seeking" lines).
- 3 extended-reflection insights that reached deep memory (with date, confidence).
- For each ticker's single biggest-loss day: date, decision, the cited memories' real
  text, FinBERT sentiment, next-day return — the "why it chose wrong" material.
- The as-shipped-vs-paper discrepancy list (B7/B8/F2/D20/momentum/shorting/seeding) in
  one compact block for the 20-second GitHub-vs-paper slide.

## Rules
No retraining, no new test runs (Part A/B are pure recompute; C/D read artifacts).
$0 spend. Commit figures + CSV + excerpts. STATUS truthful. Report the reconciliation
verdict explicitly: which numbers were wrong, why, and the corrected table.
