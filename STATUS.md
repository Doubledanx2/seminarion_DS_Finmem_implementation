# STATUS.md — live project snapshot

> Claude Code: OVERWRITE this file in place after every completed step or new blocker.
> Keep under ~80 lines. History belongs in IMPLEMENTATION_LOG.md, not here.

**Last updated:** 2026-06-12 ~19:30 local
**Currently doing:** 🚂 TSLA FinMem-Ours TRAIN launched (will pace/sleep across the
00:05 UTC pool reset); personas awaiting Dan's 60-second leakage glance (STOP, test-phase only)

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
