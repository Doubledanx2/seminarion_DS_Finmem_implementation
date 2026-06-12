# Prompt for Claude Code — Stage 3: GO order (full pipeline → backtest)

Copy everything below the line into Claude Code, run from the repo root.

---

## Gate results from Dan

1. **A3 canary CONFIRMED: $0.00 billed** (10 requests, 18K tokens, free data-sharing
   pool active). OpenAI free-pool path is GO. Implement A3 step 2 (TokenMeter $4 hard
   abort + quota-aware pacing across the 00:00 UTC reset) before the first train run.
2. **Summarization: GO**, with one re-check first — the quality sample was generated
   BEFORE addendum A5 was written. Re-validate the sample against A5 (especially A5.2
   strict per-item isolation in batched requests and A5.5 no model-injected context).
   If the sample prompt already complies, proceed; if not, fix the prompt, regenerate a
   20-article sample, log the diff, and proceed without waiting.

Re-read `claude_code_prompt_02_implementation.md` (addenda A1–A5), `ARCHITECTURE.md`,
`BACKTEST_INTEGRITY.md` before starting. They are binding.

## Execution order (today's goal: smart date-keyed database + 5-ticker backtest)

1. **Full summarization** (Gemini 3.1 Flash-Lite, free tier, ~1,849 req over ~2 days,
   checkpointed). Summary store per A5.1 schema — dates from OUR pipeline only.
2. **FinBERT sentiment** (finbert-tone + B7 fix) over all summaries.
3. **env_data pickles** for all 5 tickers → `data/03_model_input/`. Validate each by
   stepping MarketEnvironment end-to-end.
4. **Leakage test T1–T4** (A5.4 added) — must be green before any LLM run.
5. **A4 items, in order:** B8 verification (self-adaptive persona absent as-shipped —
   confirm, document, add config-flagged paper-rule variant); momentum 3-vs-7
   documentation; **draft 5 persona strings (pre-2025-02 facts ONLY) → write to
   config/ → STOP for Dan & Nimrod's review**; position accounting (direction-based
   primary, long-only clamp in portfolio.py); pin sampling params; tiktoken mapping;
   verify top_k=5 in ALL configs.
6. **Hyperparameter-freeze commit** (Sin 3): commit configs + code state, record hash
   in STATUS.md, BEFORE the first test run.
7. **Train runs** (5 tickers, gpt-4.1-mini, memory population, 2025-02-01 → 2025-12-31).
   Pace within the 2.5M/day mini pool; checkpoint-resume across days; never let one
   request overflow the remaining daily quota.
8. **Test runs** (2026-01-02 → 2026-06-01), as-shipped persona variant = main result.
9. **Portfolio layer** (A-extension, isolated module) on test days.
10. **Baselines:** Buy & Hold per ticker + equal-weight portfolio; no-memory ablation.
11. **gpt-4.1 TSLA fidelity run** (~$3) — only after main run completes and Dan approves
    the spend.
12. **Metrics v2:** with/without 10 bps + 0–50 bps break-even sweep, Wilcoxon, bootstrap
    CI, top-5-day contribution, per-month returns, guardrail-failure rate per model.
13. **Streamlit replay dashboard** (read-only over checkpoints).

## Standing rules (unchanged)

- STATUS.md overwritten after every step/blocker; IMPLEMENTATION_LOG.md appends all.
- Money gates: STOP for approval before any paid run > $2; sec-api ≤ 50 credits total.
- No test-set tuning, ever. BACKTEST_INTEGRITY.md boxes checked off as implemented.
- Two planned STOPs in this stage: persona review (step 5) and fidelity-run spend (step 11).
  Everything else runs without waiting.
