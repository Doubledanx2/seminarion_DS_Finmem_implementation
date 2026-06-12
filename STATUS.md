# STATUS.md — live project snapshot

> Claude Code: OVERWRITE this file in place after every completed step or new blocker.
> Keep under ~80 lines. History belongs in IMPLEMENTATION_LOG.md, not here.

**Last updated:** 2026-06-12 ~20:15 local
**Currently doing:** 🌙 **Overnight automation: ARMED, next fire 03:10** (Israel).
Stage-8 queue runs unattended; watchdog 03:30–09:30 every 2h; morning report 08:30.

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

## Overnight run — morning summary (2026-06-12 20:11)
- Grid: 0/12 run-steps complete; REMAINING: TSLA_train, TSLA_test, NFLX_train, NFLX_test, AMZN_train, AMZN_test, MSFT_train, MSFT_test, COIN_train, COIN_test, TSLA_nomem_test, portfolio_layer
- RESULTS_FINMEM_OURS.md: present
- Chat spend: paid ~ $0.00 of $3.00 cap (865 lifetime calls)
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
