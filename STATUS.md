# STATUS.md — live project snapshot

> Claude Code: OVERWRITE this file in place after every completed step or new blocker.
> Keep under ~80 lines. History belongs in IMPLEMENTATION_LOG.md, not here.

**Last updated:** 2026-06-13 ~13:30 local
**Currently doing:** Stage 11 COMPLETE — metrics AUDITED & corrected, deck figures +
excerpts rendered. Remaining: optional Streamlit dashboard + STOP #2 (gpt-4.1 fidelity).

## 🔎 METRICS AUDIT (Stage 11) — we caught our own bug
Independent recompute disagreed with our committed numbers. **Two bugs found & fixed:**
1. **Terminal-day truncation** — priced on the portfolio series, which dropped the final
   test day 2026-06-01 (a −4.57% TSLA day). B&H TSLA was −0.5%, **true −5.07%**.
2. **Shorting-on-sell** — metrics used raw decisions as the position (hold=flat,
   **sell=SHORT**), inflating every strategy (NFLX no-mem +57% → true **+19.8%**).
Canonical convention now enforced (`16_canonical_metrics.py`): carry-forward unit
long-only {0,+1} × simple next-day return, compounded, on the FULL env series; a
**regression assertion** fails the run unless B&H == P[last]/P[first]−1 (TSLA −5.07% ✓).
Reconciliation: `15_reconcile.py`. Our canonical now matches the independent audit exactly.

## 🎯 HEADLINE RESULT (audited, leakage-free, test 2026-01-02→06-01, 0bps)
| | mean CR | per-ticker CR (TSLA/NFLX/AMZN/MSFT/COIN) |
|---|---|---|
| FinMem-Ours | **−5.3%** | −23.1 / +3.8 / +15.5 / −3.9 / −18.5 |
| Buy & Hold | **−4.1%** | −5.1 / −5.6 / +15.3 / −2.2 / −22.8 |
| No-memory | **+1.7%** | −5.5 / +19.8 / +24.5 / −6.0 / −24.2 |
- **FinMem-Ours underperforms Buy & Hold** on the mean; **no-memory is best** and beats
  full FinMem-Ours on **3/5** tickers. The layered memory did not add value out-of-sample.
- Ours vs B&H pooled Wilcoxon p=0.69 (n.s.); Ours vs no-mem p=0.075 (median −28 bps/day).
- Momentum-agreement 100% (as-shipped) → 74% (Ours). As-shipped TSLA canonical −9.2%.
- The earlier "+12.3% vs −2.4%" headline was a metrics-bug artifact — **corrected**.
- The memory machinery DID engage (1000+ retained, agent cites its own reflections) —
  it just didn't help returns. Coherent F1/F2/F3 critical-assessment story stands.

## Deliverables (Stage 10–11, committed)
- `data/09_results/metrics_canonical.{md,csv}` — audited table the deck quotes (CR, ann
  ret/vol, Sharpe, Sortino, MDD, alpha/beta, turnover, %long @0&10bps; Ours/no-mem/B&H/as-shipped).
- `RESULTS_FINMEM_OURS.md` — narrative, canonical, with corrected-metric banner.
- `data/09_results/figures/` — 17 PNGs (equity ×5, cum & Sharpe bars, break-even ×5,
  NFLX persona timeline, citation share, PCA vector-DB NFLX+TSLA, deep-layer growth).
- `data/09_results/deck_excerpts.md` — 2 reconstructed prompts, persona quotes, extended
  reflections, biggest-loss-day material, GitHub-vs-paper discrepancy table.
- `DEEP_DIVE*.md` ×6 · `DEEP_LAYER_TRACE.md` (F2) · error_pack ×5 · `IMPLEMENTATION_LOG.md`.

## 🔒 Freeze commits
- as-shipped exhibit: `f170a92` · **FinMem-Ours: `96d724d`** (freeze #3).

## Spend meters
- sec-api 31/100 · Gemini $6.95 (closed) · ada-002 ~$1.50 · OpenAI chat paid
  **$1.66 / $3.00 cap**. Stage 11 = $0 (pure recompute + artifact reads).

## LC-Trader baseline (Stage 12, TSLA only — "stop after tesla")
Plain long-context trader, NO FinMem (no persona/memory/retrieval/FinBERT); append-only
news+filings context, prompt-cache optimized. **TSLA: CR −7.9%** (Sharpe −0.33; 100 hold /
2 buy / 1 sell → bought early & held, 98% days long) — **beats FinMem-Ours −23.1%**, tracks
near B&H −5.1% / no-mem −5.5%. **97% cache-hit → $0.78** (vs $2.82 no-cache). Cost scales
~quadratically with horizon (context grows to 135K tok). Files: `LC_TRADER.md`,
`lc_trader.py`, folded into metrics_canonical + equity_TSLA/bars figures. (Other 4 tickers
not run; ~$1–2 more if wanted.) → reinforces F3: the memory apparatus subtracted value.

## Open / next
1. (optional) extend LC-Trader to NFLX/AMZN/MSFT/COIN (~$1–2, cheaper — smaller contexts).
2. **Streamlit replay dashboard** (read-only) — no quota.
3. **STOP #2 (Dan):** optional gpt-4.1 TSLA fidelity run (~$3) — backbone-sensitivity.
4. Scheduled tasks still ARMED (idempotent, ~$0 re-fire) — `schtasks /delete` to remove.

## Key findings (slide pipeline)
- **B20: we caught our own metrics bug** (terminal-day + shorting) — the audit itself is
  a slide (Sin-4/Sin-5 in practice). · **F3: memory didn't help** (no-mem ≥ Ours, mean).
- F1: as-shipped 100% momentum · F2: as-shipped deep layer 3-day revolving door ·
  B7 scrambled FinBERT labels · B8 absent self-adaptive persona · D20 Q_shallow 3 vs 14.
