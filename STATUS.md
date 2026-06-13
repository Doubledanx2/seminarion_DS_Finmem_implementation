# STATUS.md — live project snapshot

> Claude Code: OVERWRITE this file in place after every completed step or new blocker.
> Keep under ~80 lines. History belongs in IMPLEMENTATION_LOG.md, not here.

**Last updated:** 2026-06-13 ~11:30 local
**Currently doing:** Stage 10 — overnight RUNS all succeeded (6 tests × 102d + portfolio).
Fixed the 2 broken post-processors; **REAL RESULTS + 5 DEEP_DIVE files generated**.
Part B (4 no-memory ablations) running to complete the memory column.

## Stage 10 results (FinMem-Ours, leakage-free, test 2026 H1)
- **NFLX +19.1%** (Sharpe 1.22) vs B&H −5.5%, break-even **54 bps** — standout win.
- AMZN +23.8% vs B&H +19.5% (edges it). TSLA −25.8%, MSFT −7.0%, COIN −22.0% (lose).
- **Mean ≈ tied** (Ours −2.4% vs B&H −2.2% @0bps); pooled Wilcoxon p=0.79 (n.s.).
- Momentum-agreement **100% (as-shipped) → 74% (Ours)**: our fixes moved the agent off
  pure momentum-following. Deep memory now RETAINS (TSLA 1162 mem incl. 119 self-
  reflections) vs the as-shipped 3-day revolving door (F2).
- **Agent uses its own memory:** citation share short/mid/long/reflection ≈ 26/22/27/23;
  NFLX's single most-cited memory is one of its OWN extended reflections, cited 78×.
- Files: `RESULTS_FINMEM_OURS.md` (+CSV), `DEEP_DIVE.md` + `DEEP_DIVE_<TKR>.md` ×5.

## Part A fixes (all verified)
- 12_final_report: jsonl reads → `utf-8-sig` (validation_events had a BOM from an old
  PowerShell dedup; BOM also stripped from the data file). Real RESULTS now generated.
- 13_error_pack: `sys.path` repo-root (pickle.load needs `puppy`) → 5×20-day packs.
- morning report: now reads the orchestrator's own results dict + report-artifact
  predicates, counts REPORT steps, header says "INCOMPLETE — see failures" on any gap.
  **Proven**: the 08:30 task honestly reported INCOMPLETE while RESULTS was a stub
  (old bug would have said FULL GRID DONE). test-complete predicate keys off the final
  dir w/ ≥90 2026 reflections.

## Overnight automation (Stage 9) — was ARMED, grid COMPLETE

## Overnight automation (Stage 9) — ARMED
- Freeze #3: `96d724d` (6-month train window, mandatory 10-K seeding incl. MSFT FY2024
  [sec-api 31/100], 10 seeds total, Jul–Dec personas numerically SELF-VERIFIED,
  TokenMeter paid-overflow: free pool → paid ≤ **$3.00 cap**, switchover logged).
- `run_overnight.py`: idempotent done-predicates, sim-checkpoint resume, lockfile
  (live-PID collision tested), 3-min heartbeat → overnight.log, traceback-and-continue.
- schtasks all "Ready": FinMemOurs_Overnight 03:10 · _Watchdog 03:30 +2h×6h ·
  _Morning 08:30; launchers C:\Users\dansh\finmem_*.bat (PYTHONUTF8=1 + full paths —
  live trigger test caught & fixed a cp1255 crash under Task Scheduler).
- Dry-run 15/15 GREEN (preflight ran real checks: configs, seeds, persona verify, T1–T4).
- **Dan tonight:** ✅ disk 82.8GB ✅ .env ✅ AC-sleep=Never → ☐ keep laptop PLUGGED IN,
  lid open (or lid action = nothing), stay logged in (lock OK, no log-off/shutdown).

## Overnight run — morning summary (2026-06-13 08:30)
- 14/15 steps complete — INCOMPLETE — see failures: final_report
- RESULTS_FINMEM_OURS.md: MISSING or stub
- error pack: present
- Chat spend: paid ~ $1.30 of $3.00 cap (2651 lifetime calls)
- Log tail: see overnight.log
## 🔒 Freeze commits
- as-shipped main: `f170a92d…` (TSLA train+test COMPLETE — kept as the before/after exhibit)
- **FinMem-Ours: `2975839393511daaad982d3c011f4b15c5db28df`** (2026-06-12)
  paper_rule persona (3d switch) · ext-reflection both phases → deep · obs=7d CR ·
  no downward jumps · pure-age recency · unit {0,+1} long-only · ada-002 (1536) ·
  filing seeding (3 pre-train filings) · long train window (declared deviation) ·
  K=5, M=7, Q=14/90/365, temp=1.0 unchanged. Pre-declared: vs B&H, vs no-memory,
  vs TSLA-as-shipped. No test-set tuning after this hash.

## Stage-7 run tracker (FinMem-Ours)
| # | Step | Status |
|---|---|---|
| 1 | TSLA train → test + first metrics | **train RUNNING** (memory events ON) |
| 2 | NFLX/AMZN/MSFT/COIN train → test | queued (sequential, quota-paced) |
| 3 | No-memory ablation (TSLA test) | pending |
| 4 | Portfolio layer over 5 test runs | pending |
| 5 | Final metrics report (md + csv) | pending |
| 6 | Error-analysis pack (20 days × 5) | pending |
| 7 | Streamlit replay dashboard | pending |
| 8 | OPTIONAL gpt-4.1 fidelity (~$3) | STOP #2 at the end |

## Cancelled (Dan's quota reallocation)
As-shipped NFLX/AMZN/MSFT/COIN test runs; standalone V-P/V-E variant runs —
superseded by FinMem-Ours. (As-shipped trains that already completed: NFLX, AMZN,
MSFT — artifacts kept on disk, unused.)

## Blockers & questions for Dan
1. **STOP (60s): persona leakage glance** — 5 train-period overview paragraphs
   (test prompts only; train prompts keep the pre-2025-02 personas). Printed in chat
   + embedded in `config/*_finmem_ours_config.toml` under `character_string_test`.
   All numbers computed from OUR price pickles, train window only (Feb–Dec 2025).
2. None else. Filing boundary audit clean: TSLA/NFLX/MSFT seeded; AMZN/COIN have no
   filings in the 90d pre-train window → no extra sec-api credits.

## Spend meters
- sec-api **30/100** · Gemini **$6.95 closed** · OpenAI chat **$0 billed** (free pool;
  ~3 quota days projected for all Stage-7 runs) · ada-002 embeddings: ~$1.50
  pre-approved (billed, not pool-covered) · $4 hard abort armed

## Key findings so far (slide pipeline)
- F1: 100% momentum agreement (TSLA as-shipped test) · F2: deep layer = 3-day
  revolving door, zero filings retained (DEEP_LAYER_TRACE.md) · B7 scrambled FinBERT
  labels · B8 absent self-adaptive persona · B14 empty-news crash · D20 Q_shallow 3 vs 14
- As-shipped TSLA exhibit: CR −1.9% (0bps) vs B&H −0.5%; break-even 0bps

## Last 5 actions
- 19:25 TSLA FinMem-Ours train launched (seeded filings, events log ON)
- 19:20 FREEZE COMMIT FinMem-Ours `2975839…` pushed
- 19:10 Setup: 5 configs + overviews + filing_seeds.json + boundary audit (clean)
- 18:50 FinMem-Ours behavior tests 6/6 + all regression suites green; ada-002 smoke ok
- 18:20 Code: persona-3d, ext-refl both→deep, obs-7d, no down-jumps, pure-age recency,
  unit positions, seeding, run.py overrides

## Next planned action
- On TSLA-Ours train completion: pre-flight-style sanity → TSLA-Ours TEST → first
  metrics table vs B&H vs as-shipped → fan out 4 tickers
