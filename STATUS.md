# STATUS.md — live project snapshot

> Claude Code: OVERWRITE this file in place after every completed step or new blocker.
> Keep under ~80 lines. History belongs in IMPLEMENTATION_LOG.md, not here.

**Last updated:** 2026-06-12 ~14:15 local
**Currently doing:** addendum A1–A3 executed; waiting on Dan's two checks
(OpenAI usage = $0.00, Gemini sample approval) before the full summarization run

## Stage tracker
| # | Stage | Status |
|---|---|---|
| 1 | News download (Alpaca, 5 tickers) | **done** (18,311 articles, no monthly gaps) |
| 2 | SEC 10-K/10-Q extraction (30 sec-api credits) | **done** (30/30 ok, first pass) |
| 3 | Summarization (Gemini 3.1 Flash-Lite) | **sample done, awaiting Dan's approval** |
| 4 | Sentiment (FinBERT local) | ready (B7 label fix in, stack tested) |
| 5 | env_data pickles (5 × data/03_model_input/) | not-started (needs summaries) |
| 6 | Leakage unit test (Sin-2 assert) passes | **passing** on current data; final pass after stage 5 |
| 7 | Train runs (5 tickers, gpt-4.1-mini) | **canary done (10/10 valid JSON)** — awaiting Dan's $0.00 usage check |
| 8 | Test runs (5 tickers) | not-started |
| 9 | Portfolio-layer extension runs | not-started |
| 10 | Baselines (B&H, no-memory; optional PPO) | not-started |
| 11 | gpt-4.1 TSLA fidelity run | not-started |
| 12 | Metrics ± costs, Wilcoxon, bootstrap CI | not-started |
| 13 | Streamlit replay dashboard | not-started |

## Addendum execution (2026-06-12)
- **A1 done:** `puppy/validation.py` replaces guardrails-0.3.2 (same contract: choice +
  id-membership validation, ONE re-ask w/ failed output + error, train→error-record /
  test→hold fallback). Every re-ask/fallback logged → guardrail-failure-rate metric.
  Offline contract test green (`tests/test_validation.py`, 5/5). puppy imports on 3.12.
- **A2 done:** finbert-tone confirmed in ARCHITECTURE.md §2 with B7 name-based mapping.
- **A3 step 1 done:** canary = 10 gpt-4.1-mini calls through production path
  (chat.py + TokenMeter): 10/10 valid JSON, 17,988 in / 449 out tokens.
  **→ DAN: check platform.openai.com/usage — must show $0.00 billed.**
  A3 step 2 (TokenMeter $4 hard abort) — implemented next, before train runs.

## Per-ticker data status
| Ticker | News articles | Filings (K/Q) | Summaries | env_data validated |
|---|---|---|---|---|
| TSLA | 6,146 | 2/4 | sample only | dry-run only |
| NFLX | 1,341 | 2/4 | no | no |
| AMZN | 4,776 | 2/4 | no | no |
| MSFT | 4,602 | 1/5 | no | no |
| COIN | 1,446 | 2/4 | no | no |

## Spend meters
- sec-api credits: **30 / 100 used**
- Gemini: $0.00 billed (sample: 7 req, 58.7K in / 4.1K out ≈ $0.02 list, free tier)
- OpenAI: $0.00 expected (canary: 10 calls, 18.4K tok — **pending Dan's usage check**)
- Full summarization projection: 14,551 articles via API (~1,819 req) + 3,760 free
  fallbacks + 30 filings ≈ **1,849 req → 2 free-tier days**, $0 (paid would be ~$6)

## Blockers & questions for Dan
1. **Check platform.openai.com/usage** after the canary: billed must be $0.00. If not,
   enable org Data Controls → "Share inputs and outputs with OpenAI", then I rerun canary.
2. **Review data/02_intermediate/gemini_quality_sample.md** (50 articles) → approve the
   full summarization run (~2 days on free tier, $0).

## Backtest-integrity checklist status
- Sin 2: ✓ test passing (T1 forward-only dates, T2 filedAt keying, T3 env stepping)
- Sin 3: hyperparameter-freeze commit before first test run — pending
- Sin 4: frozen params in config/tsla_gpt41mini_config.toml ✓; no test-set tuning
- Sin 7: long-only flag — to implement in portfolio.py before runs
- New metric: guardrail failure rate (A1) — instrumented ✓

## Last 5 actions
- 14:10 A1 contract test 5/5 green; puppy imports without guardrails on py3.12
- 13:55 reflection.py rewired to validation.guarded_call (originals' logic preserved)
- 13:40 A3 canary: 10/10 valid JSON via production chat path, meter recorded
- 13:30 Gemini 50-article quality sample → data/02_intermediate/gemini_quality_sample.md
- 13:20 Addendum read; keys verified present (GEMINI_API_KEY, OPENAI_API_KEY real)

## Next planned action
- On Dan's two OKs: full Gemini run (news day 1, filings + remainder day 2) → stages 4–6

## Risks / surprises
- B7 (paper fed P(Negative) as "positive" sentiment) — headline finding, slide-ready.
- ~1,849 Gemini requests vs 1,450/day free cap → run spans 2 days (checkpointed).
- gpt-4.1-mini deprecation late-2026 — keep LLM runs early.
