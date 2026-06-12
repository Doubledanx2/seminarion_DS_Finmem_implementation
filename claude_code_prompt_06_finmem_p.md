# Prompt for Claude Code — Stage 6: FinMem-P, the paper-as-described arm (NEW HEADLINE)

Copy everything below the line into Claude Code.

---

## Policy change from Dan (supersedes Stage-5 framing)

The PAPER is the spec; the GitHub artifact is evidence. We now build configuration
**FinMem-P** implementing the paper's description (discrepancies P1–P7 below, P10
pending your trace), freeze it with a second dated commit, and run it as the **new
headline arm** on all 5 tickers. The existing as-shipped runs are kept, relabeled
"FinMem-A (artifact)" — they become the comparison that quantifies the paper-vs-code
gap. V-P/V-E configs from Stage 5 are superseded by FinMem-P (fold them in).
Sin-4 discipline: FinMem-P's spec is fixed from the paper text BEFORE its first test
run (freeze commit #2 with hash in STATUS.md); no test-set tuning, pre-declared
comparisons updated to: FinMem-P vs B&H, FinMem-P vs no-memory, FinMem-P vs FinMem-A.

## FinMem-P specification (paper citations = ar5iv 2311.13743)

1. **P1 — Persona (§3.1):** sector intro + ticker business facts (existing approved
   text) PLUS a concise historical financial performance overview of the ticker
   **covering the training period only** (2025-02-01→2025-12-31), generated from our
   own price/news data (not model knowledge), ~5 lines: return, vol, drawdown, major
   moves. Test-phase prompts use the full version. Train-phase prompts use a variant
   built only from pre-2025-02 data (avoids within-train hindsight; log this reading
   as D-P1). Draft all 5 → STOP for Dan's quick review (leakage check).
2. **P2 — Self-adaptive risk (§3.1):** two-sided switching using the authors' exact
   commented-out wording; switch signal = sign of **3-day** cumulative return
   ("a brief period, such as three days"). Active in test; in train use the paper's
   initial-configured inclination (self-adaptive from day 1 of test).
3. **P3 — Extended reflection (§3.2.1b):** after each day's immediate reflection, one
   extra LLM call over the last **M=7** days' trace (decisions, returns, rationales);
   output stored in the **DEEP layer** (not reflection layer). Run it in BOTH train
   and test phases (paper intent; cost ≈ +1 call/day, still free-pool).
4. **P4 — Observation (§3.2.1):** test prompt's market indication = **cumulative
   return over the last M=7 trading days** (replaces the hardcoded 3-day momentum
   sentence). Keep the explanation text style; document the change.
5. **P5 — verify** train label mapping (down→Sell, up-or-flat→Buy) matches exactly.
6. **P6 — layers:** keep 4-layer retrieval (released prompt template is evidence of
   intent) but extended reflections → deep (per P3). Immediate-reflection rationale
   continues to feed the reflection index as today.
7. **P7 — Deep-layer retention:** in FinMem-P, **disable downward jumps** (no
   demotion); items leave a layer only via cleanup thresholds. Filings must persist
   in deep (assert in a unit test: a 10-K summary survives 100+ simulated days).
8. **P10 —** finish the Task-3 trace; if recency is boosted/reset on access in the
   artifact, FinMem-P uses pure exponential decay per paper. Report either way.
9. **Embeddings: text-embedding-ada-002** (backend="openai"). Estimated ~$1–2 total —
   within budget, no stop needed. Dim 1536 — fresh FAISS indices.
10. **Positions (Dan's rule): long-only unit position {0, +1}** — Buy = enter (or
    keep) a single long position; Hold = keep current state; Sell = exit to flat,
    only if holding; no shorting, no accumulation. Implement as `position_mode=
    "unit_long_only"` for FinMem-P (artifact accumulation stays for FinMem-A).
    Raw decisions still recorded. Metrics on this position series ± costs.
11. **Sentiment: keep FinBERT** scores as-is (env pickles unchanged).
12. Backbone gpt-4.1-mini; all other frozen values unchanged (K=5, M=7, Q=14/90/365,
    temperature, validation contract, leakage tests T1–T4 + env-side trace).

## Execution

1. Implement + unit-test all of the above offline (mocked LLM) including the new
   position accounting and the deep-retention assert.
2. Persona drafts (P1) → STOP #P for Dan & Nimrod.
3. **Freeze commit #2** (FinMem-P spec) — hash into STATUS.md.
4. Fresh TSLA train (ada-002 embeddings, extended reflection on) → TSLA test → report
   first results with metrics-v2 (vs B&H, vs no-memory, vs FinMem-A side-by-side).
5. Fan out to the other 4 tickers as quota allows. FinMem-A main runs that are still
   queued (NFLX/AMZN/MSFT/COIN tests) KEEP running — we need both arms; quota
   priority: FinMem-A completions first (they're nearly done), then FinMem-P.
6. STATUS.md: new "FinMem-P" section with per-ticker train/test state; budget meters
   include ada-002 spend. All standing rules unchanged ($4 abort, no test tuning,
   B-findings to the log).

Cost projection: ada-002 ≈ $1.50; all LLM runs ≈ $0 on the mini pool (~2× current
daily volume → expect ~2–3 quota days for both arms to complete). No other spend.
