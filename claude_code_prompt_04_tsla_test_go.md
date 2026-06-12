# Prompt for Claude Code — TSLA TEST PHASE: pre-flight validation + GO

Copy everything below the line into Claude Code.

---

## Decision: TSLA test run is APPROVED (2026-01-02 → 2026-06-01), pending the
## pre-flight checks below. Run them, report results compactly, and if ALL pass,
## start the test run without waiting. Any failure = STOP and report.

### Pre-flight A — trained state integrity
1. Load the TSLA trained agent from `05_train_model_output/TSLA` exactly the way
   `run.py` test mode will (`LLMAgent.load_checkpoint`). Verify: counter=231,
   229 reflections (2025-02-03→2025-12-30), all four memory layers load with their
   FAISS indices (dim 1024), portfolio state intact, persona_rule=as_shipped,
   long_only=true, no_memory=false.
2. Verify the test run loads THIS checkpoint and not an intermediate one from
   `06_train_checkpoint`.

### Pre-flight B — the actual prompt sent to the model (Dan's explicit ask)
3. Render and dump the EXACT final prompt string for a dry test day (assemble it
   without calling the API) into `data/04_model_output_log/tsla_test_prompt_sample.txt`.
   Check, line by line:
   a. No unfilled template placeholders — in particular the original
      `${gr.complete_json_suffix_v2}` (guardrails-era) must be replaced by our
      validation.py JSON-schema instructions; no literal `${...}` or stray
      template braces may reach the model. NOTE: the as-shipped `test_prompt` in
      prompts.py ends with a stray `}` typo — confirm what we actually send, and
      document (do NOT rewrite the prompt's wording — as-shipped fidelity; typos are
      findings, not bugs to fix silently).
   b. The investment_info block contains: persona, ≤5 memories per layer with IDs,
      sentiment explanation, momentum sentence — and NOTHING dated after the
      simulated day (spot-check against the env pickle).
   c. In TEST mode no future_record / next-day price appears anywhere in the prompt
      (grep the rendered string for any 2026 date later than cur_date and for
      "price difference").
   d. The one-sided risk-seeking line appears as-shipped (B8) — confirm it's there
      and logged as expected behavior for the main run.
4. Schema contract: confirm the test response model requires
   investment_decision ∈ {buy, sell, hold} + per-layer memory-ID fields validated
   against the retrieved ID lists, ONE re-ask, persistent-failure → "hold" + logged
   fallback event.

### Pre-flight C — decision → action → records
5. Trace the full path with a mocked LLM reply for each of buy/sell/hold:
   buy → +1 direction; sell → close-to-flat under long_only=true (raw "sell"
   preserved separately for the direction-based metric); hold → 0. Verify the
   long-only clamp can never produce negative holding_shares.
6. Verify everything the metrics need is recorded per test day:
   date, raw decision, clamped action, holding_shares, price, reasoning text,
   cited memory IDs per layer, validation events, token usage. Confirm metrics-v2
   can consume a 3-day mock of these records end-to-end (Sharpe/CR/MDD ± costs,
   Wilcoxon inputs, bootstrap inputs, guardrail-failure rate) — run its synthetic
   test once more against the EXACT record schema the test run will write.
7. Checkpoint cadence: agent + env checkpointed after every step to
   `08_test_checkpoint`, resumable via sim-checkpoint; final results to
   `09_results` (or our stage-2 equivalents — state the exact paths you'll use).

### Pre-flight D — quota & budget
8. TokenMeter state: confirm remaining daily free-pool headroom; test run is
   ~104 days ≈ 104 calls ≈ ~350K tokens — confirm it fits today's remaining quota
   or will pace across the UTC reset. $4 hard abort still armed. AMZN train may be
   running concurrently — confirm the shared daily budget arbitration between the
   two runs (who yields when headroom runs low; train yields to test).

### Report format
One compact checklist (A1–D8 pass/fail + one line each) into STATUS.md and chat,
the rendered prompt sample file path, then — if all green — "TSLA TEST STARTED" with
the run command used. While it runs: do NOT touch metrics code, configs, or prompts
(freeze discipline); B-numbered findings go to the log only.
