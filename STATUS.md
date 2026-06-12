# STATUS.md — live project snapshot

> Claude Code: OVERWRITE this file in place after every completed step or new blocker.
> Keep under ~80 lines. History belongs in IMPLEMENTATION_LOG.md, not here.

**Last updated:** 2026-06-12 ~15:30 local
**Currently doing:** full Gemini news summarization running in background (day 1 of ~2);
A3.2 + A4.1–A4.7 all implemented & tested; STOPPED on persona review (planned stop #1)

## Stage tracker
| # | Stage | Status |
|---|---|---|
| 1 | News download (Alpaca, 5 tickers) | **done** (18,311 articles, no monthly gaps) |
| 2 | SEC 10-K/10-Q extraction + Gemini summaries | **done** (30/30 extracted AND summarized) |
| 3 | Summarization (Gemini 3.1 Flash-Lite) | **running** — A5-compliant; TSLA ~1.5K/6.1K done; ~2 days total |
| 4 | Sentiment (FinBERT local) | ready, waiting on summaries |
| 5 | env_data pickles (5 × data/03_model_input/) | waiting on summaries |
| 6 | Leakage tests T1–T4 (A5.4 added) | **ALL PASSING** (env-side T4 trace arms after stage 5) |
| 7 | Train runs (5 tickers, gpt-4.1-mini) | code ready; **blocked on persona review (STOP #1)** + freeze commit |
| 8 | Test runs | not-started |
| 9 | Portfolio-layer extension | module not written yet (next code task) |
| 10 | Baselines (B&H, no-memory) | not-started |
| 11 | gpt-4.1 TSLA fidelity run | not-started (STOP #2 = spend approval) |
| 12 | Metrics v2 | not-started |
| 13 | Streamlit replay dashboard | not-started |

## Addendum execution
- **A1** ✓ validation.py (contract test 5/5) **A2** ✓ finbert-tone **A3.1** ✓ canary $0.00 (Dan-confirmed)
- **A3.2** ✓ $4.00 hard abort + never-overflow-daily-quota guard in TokenMeter (tested)
- **A4.1/B8** ✓ self-adaptive persona confirmed ABSENT as-shipped; `persona_rule` flag added
  ("as_shipped" main / "paper_rule" ablation via lookback-PnL sign)
- **A4.2** ✓ documented: momentum=3d (test prompt only) vs lookback=7d (memory feedback)
- **A4.3** ✓ 5 personas drafted (pre-2025-02 facts only) → **AWAITING DAN & NIMROD REVIEW**
- **A4.4** ✓ long_only flag (Sell→flat, raw decisions preserved) **A4.5** ✓ temperature=1.0 pinned
- **A4.6** ✓ tiktoken o200k for gpt models (+B9 fix) **A4.7** ✓ top_k=5 verified all 5 configs
- **A5** ✓ summarizer retrofit: ID-tagged batches, per-ID parse, no-background-knowledge rule,
  full store schema; 20-article regen sample clean (no injected context found — Dan may eyeball)

## Spend meters
- sec-api: **30 / 100** | OpenAI: $0.00 billed (Dan-confirmed) | Gemini: $0 (free tier;
  129 req, 0.93M in / 77K out so far today incl. filings + samples)

## Blockers & questions for Dan
1. **STOP #1 (planned): persona review** — 5 character_strings in
   `config/*_gpt41mini_config.toml`. Check: pre-2025-02 facts only, no leakage, retrieval-
   query quality. Train runs start on your OK + freeze commit.
2. FYI not blocking: B10 — Alpaca URLs aren't unique (quote-page URL shared by 7 articles);
   store re-keyed to url#timestamp, T4 green, zero summaries lost.

## Backtest-integrity checklist status
- Sin 2 ✓ T1–T4 passing | Sin 3: freeze commit pending (after persona OK)
- Sin 4 ✓ frozen params + pinned sampling; one run per config | Sin 5: metrics v2 pending
- Sin 6: metrics v2 pending | Sin 7 ✓ long_only implemented (main run = long-only)
- New metric ✓ guardrail failure rate instrumented

## Last 5 actions
- 15:25 Full news summarization relaunched with fixed IDs (background, day 1)
- 15:15 B10 found by T4: non-unique URLs → store re-keyed url#timestamp, migrated, green
- 14:55 A4 behavioral tests 6/6 green (clamp, B8 swap, $4 abort, overflow guard, tiktoken)
- 14:40 5 ticker configs generated; top_k=5 + model string verified
- 14:25 A3.2 TokenMeter hard abort + A4.1 persona_rule + A4.4 long_only implemented

## Next planned action
- Portfolio-layer module + metrics v2 skeleton while summarization runs; then sentiment +
  env pickles when summaries land; freeze commit after persona OK

## Risks / surprises
- B10 would have silently dropped 6 TSLA articles — our own leakage test caught it.
- Gemini daily cap may hit before TSLA finishes today; checkpoint-resume handles it.
- gpt-4.1-mini late-2026 deprecation — keep LLM runs early.
