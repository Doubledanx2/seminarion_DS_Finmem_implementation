# Prompt for Claude Code — Stage 5: paper-INTENT variants + deep-layer trace

Copy everything below the line into Claude Code.

---

## Context & framing (binding)

Main results = the as-shipped artifact, frozen at f170a92 — UNCHANGED, still the
headline. Everything in this stage is an **explicitly-labeled exploratory variant**
reconstructing what the PAPER DESCRIBES but the code never shipped (B8 persona
switching, extended reflection) plus instrumentation. Sin-4 discipline: these are
post-freeze additions → labeled "exploratory / paper-intent reconstruction" in all
outputs, never merged into main tables, Bonferroni note in metrics-v2 if compared.
F1 (100% momentum agreement) and the B16/hygiene fixes are acknowledged — good work.

## Task 1 — Adaptive persona variant (paper intent, V-P)

1. `persona_rule="paper_rule"` already exists. Confirm its rule matches the paper's
   description: cumulative-return sign over the lookback window (M=7, the same series
   as get_feedback_response) → risk-seeking when ≥ 0, **risk-averse when < 0**, with
   the full two-sided text from the authors' own commented-out block in prompts.py
   (use their exact wording — it's their text, maximal intent-fidelity).
2. TEST-phase only run: the train prompt carries no risk line, so the existing TSLA
   trained memory is reusable as-is. Run TSLA test with persona_rule=paper_rule
   (~104 calls, free pool). Output to a clearly separated results dir
   (e.g., 07_test_model_output/TSLA_paper_rule).
3. Report side-by-side: as_shipped vs paper_rule — CR/Sharpe/MDD ± costs, decision
   mix, momentum-agreement rate, days spent in risk-averse mode, and behavior in the
   April drawdown specifically (did it go defensive where as_shipped rode it down?).

## Task 2 — Extended reflection variant (paper intent, V-E)

The paper (and our slide 19) describes a SECOND reflection type: every trading day,
beyond the immediate reflection, the agent re-evaluates the last **M=7 trading days**
— outcomes of its immediate reflections vs realized moves — and synthesizes durable
insights into long-term memory. The code never implemented it. Build it as a
config-flagged module (`extended_reflection=true`, default false):

1. One extra LLM call per test day (after the decision): input = the last M days'
   (date, decision, reasoning summary, realized next-day return) tuples + persona;
   output = a JSON-validated synthesis (validation.py contract: {"insight": string,
   "confidence": one of low/med/high}). Write the insight into REFLECTION memory...
   per the paper's text it feeds the deep/long layer — implement destination as a
   config choice, default = reflection layer (conservative), and note the ambiguity
   as D-next (the paper says "long-term memory", the layers say reflection is its own
   index — document which reading you take and why).
2. Cost: ~104 extra calls ≈ ~80K tokens for a TSLA test run — free pool. Implement,
   unit-test offline (mocked LLM), then run TSLA test variant V-E
   (as_shipped persona + extended reflection) → 07_test_model_output/TSLA_ext_refl.
3. If quota allows after the other tickers' main runs: V-PE (paper_rule + extended
   reflection together) — the full "paper as described" reconstruction. Priority is
   below the main runs of the other 4 tickers.
4. Train-phase extended reflection: NOT now (would need retrains). Note as future work.

## Task 3 — Deep-layer code trace (free, do first — it's pure local work)

Hypothesis to confirm/refute (revolving door): entry to LONG requires importance ≥ 80,
importance decays ×0.988/day, so promoted items fall below jump_threshold_lower=80
within days and get demoted; 10-K filing summaries (importance initialized by "sample",
typically ≪ 80) cannot persist in long at all. Evidence so far: long layer = 4 items
(all Dec 29–30) at TSLA train-end, 1 item at test-end, zero filings.

1. Add structured event logging to memorydb (config-flagged, off in frozen main runs):
   `memory_events.jsonl` — {event: promote|demote|purge|ingest, id, layer_from,
   layer_to, importance, recency, access_counter, sim_date}. Zero behavior change —
   logging only. Verify with the existing unit tests that scores are untouched.
2. OFFLINE replay first (no API): reconstruct the long-layer timeline for TSLA by
   stepping the decay/jump/cleanup math over the existing checkpoints (you have
   every-step checkpoints in 06/08) — produce the full life history of (a) both 10-K
   summaries from ingestion to wherever they went, (b) the Dec-29/30 promoted items,
   (c) sticky memory 3023 (why did its recency read 0.257 at train-end when its age
   says e^(-71/14)≈0.006 — is recency reset/boosted on access? trace the exact code path).
3. Deliverable: a short markdown report (DEEP_LAYER_TRACE.md) with the verdict:
   is FinMem's deep memory structurally unable to retain knowledge? Include the
   parameter math and 2–3 reconstructed item timelines. If confirmed → finding F2,
   slide-ready.
4. The V-P / V-E runs (Tasks 1–2) run WITH memory-event logging enabled, giving us
   live traces at no extra cost.

## Ordering & budget

Task 3.2 offline replay NOW (free, no quota) → Task 1 (TSLA V-P test, ~104 calls)
→ remaining tickers' MAIN runs keep absolute priority on quota as they certify
→ Task 2 implementation + V-E run → V-PE if headroom.
All spend within existing free-pool pacing; $4 abort stays armed. STATUS.md gains a
"Variants (exploratory)" section. STOPs: none planned — report after each completes.
