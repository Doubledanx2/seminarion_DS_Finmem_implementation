# Prompt for Claude Code — Stage 8: 6-month train + overnight full-grid run

Copy everything below the line into Claude Code. Goal: ALL results by morning.

---

## Changes from Dan (supersede Stage-7 where they conflict)

1. **Train window = 6 months back from test start: 2025-07-01 → 2025-12-31** (~127
   trading days). Test unchanged (2026-01-02 → 2026-06-01). Stop/discard the sleeping
   TSLA-Ours train (it's at day 0 — nothing lost).
2. **10-K seeding is mandatory for every ticker:** at train day 1, the deep layer must
   contain the ticker's most recent 10-K as of 2025-07-01, stamped with its true
   filedAt, regardless of age. TSLA/NFLX/AMZN/COIN 10-Ks (Jan–Feb 2025 filings) are
   already extracted+summarized. **MSFT needs its FY2024 10-K (filed ~2025-07-30? NO —
   filed ~July 2024): extract item 7 via sec-api (~2–3 credits, report count) +
   Gemini-summarize.** Also seed the latest 10-Q if filed within 120 days before
   train start. Leakage rule unchanged: only filedAt ≤ seed date, true dates.
3. **Personas:** regenerate the test-phase performance-overview paragraphs for the
   NEW window (Jul–Dec 2025) from our pickles. Dan pre-approves the FORMAT; replace
   the human gate with a self-verification script that asserts every number in the
   persona text equals the pickle-computed value (fail = abort run). Print the five
   paragraphs to STATUS for the morning read.
4. **Budget change: paid overflow is AUTHORIZED tonight.** Dan deposited $5.
   ada-002 ≈ $1.50 stands. Chat spend: free pool first, then paid gpt-4.1-mini up to a
   **hard cap of $3.00** (TokenMeter abort updated accordingly; total ≤ $4.50 < $5).
   Never let one request straddle the free/paid boundary unknowingly — log the
   switchover moment.
5. **Freeze commit #3** after items 1–3 are in (window + seeding + personas), hash to
   STATUS.md. Still zero test-set tuning; TSLA-Ours test has never run, so this
   remains pre-test.

## Overnight queue (run unattended; checkpoint-resume; no human stops)

| # | Step | Est. tokens |
|---|---|---|
| 1 | Pre-flight (automated, abbreviated A–D): config sanity, seeded filings present in deep at day 0 (assert), leakage T1–T4 green on new window, persona self-verify, prompt-render dump per ticker | 0 |
| 2 | TSLA train → test → metrics table (vs B&H, vs as-shipped exhibit) | ~1.0M |
| 3 | NFLX train → test | ~1.0M |
| 4 | AMZN train → test | ~1.0M |
| 5 | MSFT train → test | ~1.0M |
| 6 | COIN train → test | ~1.0M |
| 7 | No-memory ablation: TSLA test | ~0.35M |
| 8 | Portfolio layer over the 5 completed tests | ~0.3M |
| 9 | metrics-v2 FINAL report: per-ticker CR/Sharpe/MDD ±costs (0–50bps break-even), Wilcoxon, bootstrap CI, guardrail-failure rate, momentum-agreement, top-5-day contribution, per-month returns → `RESULTS_FINMEM_OURS.md` + CSV | 0 |
| 10 | Error-analysis pack: 20 random agent-days × 5 tickers exported | 0 |
| 11 | Morning STATUS.md: full summary + money meters + anything that failed | 0 |

Total ≈ 5.7M tokens → 2.5M free (00:05 UTC reset) + ~3.2M paid ≈ **$1.60–2.00 chat
spend**, well under the $3.00 cap. If anything aborts, the queue continues with the
next ticker and the failure goes to STATUS — a partial grid by morning beats nothing.

## Standing rules

Memory-event logging ON for all runs (dashboard fuel). Validation contract, B-logging,
T1–T4, run.py override mechanism — unchanged. Streamlit dashboard and the optional
gpt-4.1 fidelity run remain for tomorrow (daylight tasks).
