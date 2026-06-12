# Prompt for Claude Code — Stage 7 (FINAL): one version, "FinMem-Ours", run to the finish

Copy everything below the line into Claude Code. SUPERSEDES the two-arm framing of
Stage 6 — there is ONE headline configuration now.

---

## Dan's direction (binding)

Our implementation = the paper's architecture + all our fixes (sins, bugs, discrepancies),
built on the existing codebase. The GitHub artifact was inspiration; we present OUR
version in class. No new branch, no rebuilds, no reinvention — everything below is
flag-flips and small diffs on modules that already exist and are tested.

## 1. Build config "FinMem-Ours" (merge of existing pieces — minimal diffs only)

- persona_rule = paper_rule, **switch window = 3 days** (paper §3.1 "such as three days")
- extended_reflection = true, **destination = deep layer**, both phases
- observation: **M=7-day cumulative return** in the test prompt (replaces 3-day momentum)
- memorydb: **downward jumps disabled** (deep retention; F2 fix). If the Task-3 trace
  confirmed recency-boost-on-access, disable that too — pure exponential decay.
- embeddings: **ada-002** (backend="openai", dim 1536) — ~$1.50, pre-approved
- positions: **unit long-only {0,+1}** — Buy=enter/keep, Hold=keep, Sell=exit only if
  holding. Cap holding_shares at 1; raw decisions still recorded.
- personas: existing approved texts + a ~5-line train-period (2025-02→12) performance
  overview per ticker, computed from OUR price data (return, vol, MDD, biggest moves).
  Test prompts use it; train prompts use the pre-2025-02 version. → STOP for Dan's
  60-second leakage glance, then proceed.
- **recency = pure age-based exponential decay** (trace confirmed the artifact resets
  delta on promotion — that's the echo-chamber mechanism; FinMem-Ours uses
  time-since-arrival per the paper, no reset on promotion/access).
- **filing seeding (new, from the F2 trace's boundary finding):** on simulation day 1,
  ingest any 10-K/10-Q filed within 90 days BEFORE train start, stamped with its true
  filedAt date (leakage-safe past data; fixes TSLA's FY2024 10-K filed 2025-01-30,
  3 days before train start, which was never ingested at all). Check all 5 tickers
  for the same boundary gap and report counts.
- **train window confirmed by Dan: keep the long train, 2025-02-01 → 2025-12-31**
  (declared deviation from the paper's ~72-day train; disclosed on the methods slide).
- extended-reflection destination = deep is now SAFE because downward jumps are
  disabled — these two changes ship together (D25 resolved).
- V-P window correction: 3-day CR sign per paper §3.1, NOT the Stage-5 config's M=7.
- everything else unchanged: gpt-4.1-mini, K=5, M=7, Q=14/90/365, temperature pinned,
  FinBERT kept, validation contract, TokenMeter guards, T1–T4 must pass.
- **Freeze commit "FinMem-Ours"** → hash to STATUS.md. Pre-declared comparisons:
  FinMem-Ours vs B&H, vs no-memory, vs TSLA-as-shipped (the one completed artifact run).

## 2. Quota reallocation (time-saver, Dan-approved)

- CANCEL remaining as-shipped test runs (NFLX/AMZN/MSFT/COIN) and any queued V-P/V-E
  standalone variants — superseded. Keep completed TSLA as-shipped results as the
  before/after exhibit. All quota goes to FinMem-Ours.

## 3. Run order (everything checkpoint-resumable, ~3–4 quota days, ~$1.50 total)

1. TSLA train → test under FinMem-Ours (memory-event logging ON — feeds the dashboard).
   Report first results immediately (metrics-v2 full table vs B&H vs as-shipped).
2. Fan out: NFLX, AMZN, MSFT, COIN train → test as quota allows.
3. No-memory ablation: TSLA test only.
4. Portfolio layer over the 5 completed test runs (one pass, ~104 calls).
5. Final metrics report: per-ticker CR/Sharpe/MDD ± costs (0–50bps break-even),
   Wilcoxon, bootstrap CI, guardrail-failure rate, momentum-agreement rate,
   top-5-day contribution, per-month returns. One markdown + one CSV.
6. Error-analysis pack: 20 random agent-days per ticker exported (prompt, retrieved
   memories, decision, reasoning, next-day outcome) for manual review.
7. Streamlit replay dashboard (read-only over checkpoints/logs/memory-events):
   date scrubber, per-layer retrieved memories, persona state (incl. which risk mode
   was active), reasoning chain, action, equity curve vs B&H, portfolio weights.
8. OPTIONAL (ask Dan at the end): gpt-4.1 TSLA fidelity run (~$3, STOP #2 as before).

## 4. Standing rules unchanged

STATUS.md after every step; IMPLEMENTATION_LOG numbering continues; $4 abort armed;
no test-set tuning after the FinMem-Ours freeze; B-findings logged not silently fixed;
the only STOPs: persona glance (step 1) and the optional fidelity spend (step 8).
