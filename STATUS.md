# STATUS.md — live project snapshot

> Claude Code: OVERWRITE this file in place after every completed step or new blocker.
> Keep under ~80 lines. History belongs in IMPLEMENTATION_LOG.md, not here.

**Last updated:** 2026-06-12 ~13:15 local
**Currently doing:** all key-independent Stage-2 prep done (summarizer, leakage test,
local embeddings, FinBERT fix, chat meter) — blocked on GEMINI_API_KEY

## Stage tracker
| # | Stage | Status |
|---|---|---|
| 1 | News download (Alpaca, 5 tickers) | **done** (18,311 articles, no monthly gaps) |
| 2 | SEC 10-K/10-Q extraction (30 sec-api credits) | **done** (30/30 ok, first pass) |
| 3 | Summarization (Gemini 3.1 Flash-Lite) | **blocked** — GEMINI_API_KEY not in .env |
| 4 | Sentiment (FinBERT local) | not-started |
| 5 | env_data pickles (5 × data/03_model_input/) | not-started (dry-run format validated) |
| 6 | Leakage unit test (Sin-2 assert) passes | in-progress (test written, runs on raw+dry-run; final pass needs env_data) |
| 7 | Train runs (5 tickers, gpt-4.1-mini) | blocked — OPENAI_API_KEY is placeholder |
| 8 | Test runs (5 tickers) | not-started |
| 9 | Portfolio-layer extension runs | not-started |
| 10 | Baselines (B&H, no-memory; optional PPO) | not-started |
| 11 | gpt-4.1 TSLA fidelity run | not-started |
| 12 | Metrics ± costs, Wilcoxon, bootstrap CI | not-started |
| 13 | Streamlit replay dashboard | not-started |

## Per-ticker data status
| Ticker | News articles | Filings (K/Q) | Summaries | env_data validated |
|---|---|---|---|---|
| TSLA | 6,146 | 2/4 | no | dry-run only |
| NFLX | 1,341 | 2/4 | no | no |
| AMZN | 4,776 | 2/4 | no | no |
| MSFT | 4,602 | 1/5 | no | no |
| COIN | 1,446 | 2/4 | no | no |

## Spend meters
- sec-api credits: **30 / 100 used** (extraction complete; 0 failures)
- Gemini: $0.00 spent / est. $7.25 ceiling (free tier preferred)
- OpenAI: $0.00 spent / est. $3.50 ceiling (data-sharing free pool preferred)

## Blockers & questions for Dan
1. **GEMINI_API_KEY missing from .env** → blocks summarization quality sample + full run.
   Add `GEMINI_API_KEY = "..."` to .env (aistudio.google.com/apikey).
2. **OPENAI_API_KEY is still the placeholder** in .env → blocks stages 7+ (not needed
   for summarization). Needed by the time train runs start.
3. **Q1: FinBERT variant** — ARCHITECTURE.md says ProsusAI/finbert, authors' code uses
   yiyanghkust/finbert-tone. Recommend finbert-tone (repo-faithful, labels now fixed).
   Say the word and I'll switch otherwise.

## Backtest-integrity checklist status
- Sin 2: filedAt indexing ✓ (filings indexed by EDGAR filedAt/acceptanceDateTime);
  16:00-rule ✓ (kept, leakage-conservative); cutoffs recorded (gpt-4.1-mini Jun-2024,
  Gemini 3.1 Flash-Lite Jan-2025, FinBERT pre-2020, bge-large n/a-local); unit test
  written (`tests/test_leakage.py`), final pass pending env_data.
- Sin 3: hyperparameter-freeze commit pending (before first test run).
- Sins 1,4,5,6,7 + beyond: tracked, not yet at the implementation point.

## Last 5 actions
- 2026-06-12 ~12:30 Sin-2 leakage test PASSING on current data (T1/T2/T3)
- 2026-06-12 ~12:45 Local embedding backend (bge-large/3090) added, factory in memorydb
- 2026-06-12 ~12:55 chat.py: TokenMeter + daily-quota pacing, payload filtering (tested)
- 2026-06-12 ~13:05 **BUG B7 found in authors' code: FinBERT labels scrambled** (their
  "positive" = P(Negative)); fixed by name-based mapping; local stack smoke test green
- 2026-06-12 ~13:15 Stage-2 config tsla_gpt41mini_config.toml (frozen hyperparams)

## Next planned action
- On GEMINI_API_KEY arrival: run 50-article quality sample → show Dan → full summarization

## Risks / surprises
- **B7:** the paper's sentiment annotations were scrambled (finbert-tone label-order
  bug in their pipeline) — big talking point for the presentation.
- Alpaca feed is 100% Benzinga (single source) — disclosed as data limitation.
- GPT-4.1(-mini) API retirement during 2026 (final Oct-2026) — finish LLM runs early.
