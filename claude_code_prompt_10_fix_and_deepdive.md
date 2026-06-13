# Prompt for Claude Code — Stage 10: fix reports + decision/memory deep-dive pack

Copy everything below the line into Claude Code. The overnight RUNS all succeeded
(6 test runs × 102 days + portfolio layer); only the two post-processing scripts
failed. Fix those, then build the deep-dive Dan asked for.

---

## Part A — fix the broken reporting (no new compute)

1. `12_final_report.py` crashed: `JSONDecodeError: Unexpected UTF-8 BOM` reading
   `validation_events.jsonl`. Open all jsonl reads with `encoding="utf-8-sig"` (or
   strip BOM). Re-run → produce the REAL `RESULTS_FINMEM_OURS.md` (currently it's
   empty stubs saying "TEST NOT COMPLETE" — that predicate is wrong; the runs ARE
   complete at 102 test days each).
2. `13_error_pack.py` crashed: `ModuleNotFoundError: No module named 'puppy'` — run it
   with repo root on PYTHONPATH (or `python -m`). 
3. **Fix the false "12/12 FULL GRID DONE" summary**: the morning report must count
   REPORT steps too and must read FAILED from the orchestrator's own end-state dict.
   It literally printed "DONE" while final_report and error_pack were FAILED — that
   can never happen again. Add an assertion: if any step != done, the summary header
   says "INCOMPLETE — see failures".
4. Verify the "TEST NOT COMPLETE" predicate: it should key off the FINAL output dir
   (`07_test_model_output/<TKR>_ours`, 102 reflections ≥ 2026-01-01), not a stale path.

## Part B — run the missing ablations (small, free-pool)

5. **No-memory ablation on NFLX/AMZN/MSFT/COIN** (we only have TSLA). Needed before we
   generalize "memory helped/hurt." ~4×104 calls ≈ 0.4M tokens. Report each vs its
   FinMem-Ours and B&H.

## Part C — RESULTS_FINMEM_OURS.md must contain (the real metrics)

Per ticker AND mean: CR, Sharpe, MDD — with AND without costs (0/10 bps + 0–50 bps
break-even); FinMem-Ours vs B&H vs no-memory vs (TSLA only) as-shipped. Plus Wilcoxon
signed-rank (FinMem-Ours vs B&H daily returns, pooled and per-ticker), moving-block
bootstrap 95% CI on Sharpe, decision mix, guardrail-failure rate, momentum-agreement
rate, top-5-day return contribution, per-month returns. One md + one CSV.

## Part D — DECISION & MEMORY DEEP-DIVE (new — Dan's main ask)

Build `DEEP_DIVE_<TKR>.md` for each of the 5 tickers (and an index `DEEP_DIVE.md`),
sourced from the test checkpoints + run logs + memory-event log. Each contains:

1. **Adaptive-persona timeline:** per test day, which risk mode was active
   (risk-seeking vs risk-averse, from the 3-day CR sign), the decision, and the
   realized next-day return. Summary stats: # days in each mode, # mode switches,
   decision mix within each mode, and hit-rate (did risk-averse days avoid losses?).
   Include 3–4 VERBATIM examples of the agent switching mode (quote the reasoning text
   showing "risk-seeking"/"risk-averse" language) with the surrounding price action.
2. **What the model leaned on:** for ~10 pivotal days per ticker (biggest wins/losses,
   mode switches), dump the ACTUAL retrieved memories per layer — id, date, layer,
   the real summary text, FinBERT sentiment, and whether the agent CITED it in its
   decision. Show concretely "it bought because it retrieved [these news items]".
3. **Extended reflections:** list the extended-reflection insights that reached the
   deep layer (the `[extended reflection, confidence=...]` items), with dates and
   confidence; show 3–5 verbatim. Note whether any were later RETRIEVED and cited in
   a subsequent decision (did the agent's self-criticism actually feed back in?).
4. **Memory-reliance profile:** distribution of citations across layers
   (shallow/mid/deep/reflection) — does the agent lean on news, filings, or its own
   reflections? Most-cited memory per ticker and how many times.
5. **Notable failures:** 2–3 days where the cited memories clearly contradicted the
   decision, or where it traded against strong sentiment — error-analysis fuel.

Keep each file readable (real quotes, not dumps). These feed the presentation's
results + error-analysis sections and the live demo.

## Rules

No re-runs of completed train/test (use checkpoints). Free pool for the 4 ablations,
$3 cap stays. STATUS.md truthful after each part. Report when A+C produce a real
RESULTS file and the 5 DEEP_DIVE files exist.
