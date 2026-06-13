# STATUS.md — live project snapshot

> Claude Code: OVERWRITE this file in place after every completed step or new blocker.
> Keep under ~80 lines. History belongs in IMPLEMENTATION_LOG.md, not here.

**Last updated:** 2026-06-13 ~11:45 local
**Currently doing:** Stage 10 COMPLETE — reports fixed, all ablations in, headline result
locked. Remaining: optional Streamlit dashboard + STOP #2 (gpt-4.1 fidelity, Dan's call).

## 🎯 HEADLINE RESULT (leakage-free, test 2026-01-02→06-01, 5 tickers)
**The layered memory module did NOT add value and HURT on average.**
- No-memory ablation mean CR **+12.3%** vs FinMem-Ours **−2.4%** vs B&H **−2.2%** (0bps).
- Memory helped (or tied) the memoryless agent on **5/5** tickers; hurt clearly on 3
  (NFLX +57% no-mem vs +19% ours; AMZN +47% vs +24%; TSLA −11% vs −26%).
- Ours-vs-no-memory pooled Wilcoxon p=0.13 (median −14 bps/day; not sig. at the daily
  level — edge concentrates in a few big rally days the memoryless agent caught).
- FinMem-Ours vs B&H: mean tied, pooled Wilcoxon p=0.79. NFLX is the one clear win
  (+19.1%, Sharpe 1.22, break-even 54 bps).
- Momentum-agreement 100% (as-shipped) → 74% (Ours): our fixes did change behavior;
  it just didn't help. Deep memory now RETAINS (1162 mem incl. 119 self-reflections)
  — the agent even cites its own reflections (NFLX top memory cited 78×) — yet the
  net effect on returns is negative. Strong, coherent critical-assessment story.

## Deliverables (all generated, committed)
- `RESULTS_FINMEM_OURS.md` + `data/09_results/results_finmem_ours.csv` (per-ticker +
  mean, Ours/B&H/no-mem/as-shipped, per-ticker + pooled Wilcoxon, bootstrap Sharpe CI,
  decision mix, guardrail rate, momentum-agreement, top-5-day share, per-month).
- `DEEP_DIVE.md` + `DEEP_DIVE_<TKR>.md` ×5 (persona timeline + verbatim switch quotes,
  pivotal-day retrieved memories w/ real text + FinBERT sentiment, extended reflections,
  memory-reliance profile, notable failures).
- `data/09_results/error_pack/<TKR>_20days.json` ×5 · portfolio_layer_result.json.
- `DEEP_LAYER_TRACE.md` (F2), `IMPLEMENTATION_LOG.md` (all bugs/decisions/findings).

## Part A fixes (Stage 10) — all verified
- 12_final_report: jsonl reads → `utf-8-sig` (validation_events.jsonl carried a BOM from
  an old PowerShell `-Encoding utf8` dedup; BOM stripped from the file too).
- 13_error_pack: `sys.path` repo-root so pickle.load can import `puppy`.
- run_overnight morning_report: authoritative (reads orchestrator results dict + real
  report-artifact predicates, counts report steps, "INCOMPLETE — see failures" on any
  gap, persists orchestrator_state.json). Proven both ways: honest INCOMPLETE at 08:30
  when RESULTS was a stub; honest "15/15 FULL GRID DONE" once real.

## 🔒 Freeze commits
- as-shipped exhibit: `f170a92` (TSLA train+test; CR −1.9%, 100% momentum, F2 trace).
- **FinMem-Ours: `96d724d`** (freeze #3): paper architecture + all our fixes; 6-month
  train 2025-07-01→12-31; mandatory 10-K seeding ×5; paper_rule persona (3d) · ext-refl
  both phases→deep · obs=7d · no down-jumps · pure-age recency · unit {0,+1} · ada-002.

## Spend meters
- sec-api 31/100 · Gemini $6.95 (closed) · ada-002 embeddings ~$1.50 · OpenAI chat
  paid **$1.66 / $3.00 cap** (free pool exhausted by the grid; ablations ran on paid).

## Open / next
1. **Streamlit replay dashboard** (read-only over checkpoints/logs/memory-events) — last
   build task; no quota.
2. **STOP #2 (Dan):** optional gpt-4.1 TSLA fidelity run (~$3) — backbone-sensitivity check.
3. Scheduled tasks (FinMemOurs_Overnight/Watchdog/Morning) remain ARMED — idempotent, so
   tonight's re-fire only regenerates reports at ~$0; remove via `schtasks /delete` if unwanted.

## Key findings (slide pipeline)
- **F3 (NEW): memory hurt** — no-memory beats FinMem-Ours on leakage-free data (above).
- F1: as-shipped 100% momentum agreement · F2: as-shipped deep layer = 3-day revolving
  door, zero filings retained · B7 scrambled FinBERT labels · B8 absent self-adaptive
  persona · B14 empty-news crash · D20 Q_shallow 3 vs 14.
