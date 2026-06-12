# Implementation Log — FinMem Reproduction (Stage 1: Data Gathering)

MBA data-science seminar. Reproducing FinMem (Yu et al., arXiv:2311.13743) on a
**post-knowledge-cutoff window (2025-01-01 → 2026-06-01)** to eliminate the
pre-training-leakage flaw we identified in the paper's original test window.

Every bug, fix, decision, and data-quality observation goes here (newest at the bottom
of each section). This file feeds the "implementation challenges" section of the
30-minute implementation presentation.

---

## Decisions

| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| D1 | 2026-06-12 | Repo pushed to GitHub (`Doubledanx2/seminarion_DS_Finmem_implementation`); `.env` added to `.gitignore` **before** the first commit | Original `.gitignore` did not exclude `.env`, which holds Alpaca/SEC/OpenAI keys — would have leaked secrets to a public repo |
| D2 | 2026-06-12 | Backbone-LLM candidate: **GPT-4.1** (knowledge cutoff **June 2024**) as the GPT-4-Turbo-class equivalent | Both train (2025) and test (2026) windows postdate its cutoff → zero pre-training leakage, the centerpiece of our design. Newer GPT-5.x models have cutoffs as late as Dec 2025, which would touch our test boundary. **Pending user confirmation.** |
| D3 | 2026-06-12 | SEC filings index built from the **free EDGAR submissions API** instead of sec-api.io's Query API | Saves ~10+ sec-api credits; only the Extractor calls (30 total) need the paid API. Exact counts verified: 9 × 10-K + 21 × 10-Q across the 5 tickers in-window |
| D4 | 2026-06-12 | Kept the paper's 200-articles-per-day cap and its ">16:00 → next day 09:00" news-date rounding | Comparability with the paper's pipeline; the rounding is leakage-conservative (late news only ever moves *forward* in time) |
| D5 | 2026-06-12 | News download done day-by-day per ticker with per-day parquet caching | Matches paper design, makes the 517-day pull resumable after rate-limit or network failures |

## Bugs found in the original research code & fixes

| # | File | Bug | Fix |
|---|------|-----|-----|
| B1 | `data-pipeline/01_Alpaca_News_API_download.py` | Pagination requests use `symbol=` (wrong param name — API expects `symbols`) and omit `start`/`end`, so every follow-up page silently returns **unfiltered market-wide news** | Rewrote as `01_alpaca_news_download_v2.py`: pagination repeats the full original query plus `page_token` |
| B2 | same | `round_to_next_day` builds `pl.datetime(y, m, day+1)` — invalid date on month ends (e.g., Jan 31 → "Jan 32") | v2 uses `dt.offset_by("1d")` |
| B3 | same | Article `content` field is empty unless `include_content=true` is passed — yet `03-summary.py` summarizes the body | v2 passes `include_content=true` |
| B4 | `data-pipeline/05-get_sentiment_by_ticker.py` | Reads env-data keys `filling_q`/`filling_k` (double-l typo) while `04-data_pipeline.py` writes `filing_q`/`filing_k`; also env_data is a *tuple* there but a *dict* in `puppy/environment.py` | To fix when we reach step 5 |
| B5 | `data-pipeline/03-summary.py`, `04-data_pipeline.py`, `05-...py` | Hardcoded authors' Linux paths (`/home/hfsladmin/...`, `/home/yyu/YJ/...`) and hardcoded ticker lists from a *different* experiment (BAC, DIS, GM, MRNA, NVDA, PFE — not the paper's 5) | Will parameterize per script as we reach each step |
| B6 | `data-pipeline/03-model_wrapper.py` | Uses the pre-1.0 `openai.ChatCompletion` API (removed in openai>=1.0); class `Together` shadows the imported `langchain_together.Together` | To fix at summarization step |

## Environment notes

- Windows 11, Python **3.12.7** (repo targets 3.10 — no incompatibilities hit so far).
- Installed: polars 1.41.2, vaderSentiment, clean-text. Already present: httpx, pandas, yfinance, torch 2.9 (CUDA), transformers 5.3.
- Hebrew-locale console (cp1255) breaks `print()` of article text → all pipeline runs use `PYTHONUTF8=1`.
- `gh` CLI absent; pushed with plain git + Windows credential manager.

## Data-quality observations

- **COIN**: in the paper it was a recent IPO with no DRL-training history, which drove the
  "FinMem wins where DRL can't train" story. In our 2025–26 window COIN has ~5 years of
  history, so that baseline asymmetry disappears — the DRL baselines get a fair shot on
  all 5 tickers. (Changes the baseline narrative in the presentation.)
- MSFT has only **1** 10-K in-window (June fiscal year end → FY2025 10-K filed 2025-07-30;
  the FY2026 one lands after our window). Other 4 tickers have 2 each.
- **TSLA Alpaca news (validated 2026-06-12):** 6,146 articles over 2025-01-01→2026-06-01;
  every month covered (256–513 articles/month); mean ~12/day, max 46/day — the paper's
  200/day cap never binds. 100% of articles are from **Benzinga** (Alpaca's news feed is
  Benzinga-only) — a source-diversity limitation vs the paper's Refinitiv/Reuters private
  dataset; worth a slide in error analysis. ~15% of articles carry headline+summary but
  an empty `content` body (summarization will fall back to headline+summary for those).
  One stray article stamped 2024-01 returned by the API inside the window query — will be
  filtered by the date window in `04-data_pipeline`.
- **All 5 tickers downloaded (2026-06-12), 18,311 articles total, no monthly gaps:**

  | Ticker | Articles | Monthly range | Note |
  |--------|---------:|---------------|------|
  | TSLA | 6,146 | 256–513 | richest feed |
  | AMZN | 4,776 | 199–418 | |
  | MSFT | 4,602 | 176–347 | |
  | COIN | 1,446 | 49–122 | |
  | NFLX | 1,341 | 25–136 | sparsest; Feb–Mar 2025 dip (25/33 articles) but never zero |

  All Benzinga-sourced. The paper's 200-articles/day cap never binds (max observed: 46/day).
- **Summarization cost estimate (chars/4 heuristic + 200-token summaries):**
  ~15.2M input + ~3.7M output tokens over 18,311 articles →
  gpt-4.1 ≈ **$60** · gpt-4.1-mini ≈ **$12** · gpt-5.4 ≈ $93 (Batch API halves these).
  Awaiting user approval before any spend.
- **Dry-run plumbing check passed (2026-06-12):** built a TSLA env-data pickle in the
  final `puppy` format from real prices (353 trading days, 2025-01-02→2026-06-01, via
  yfinance adjusted close) + real news with placeholder summaries + empty filings;
  `MarketEnvironment` validated the schema and stepped correctly
  (`00_dryrun_env_check.py`). So the only untested links are the paid ones
  (GPT summaries, SEC extraction).
- **Weekend/holiday news loss (paper behavior):** env_data is keyed on *trading days*
  (price dates), so news dated Sat/Sun/holidays never reaches the agent — 884/6,146
  TSLA articles (14.4%) are dropped. The paper's own pipeline does the same. Kept for
  comparability; candidate improvement (+error-analysis slide): roll weekend news
  forward to the next trading day.

## Stage-2 environment notes (for later)

- `puppy` package needs `faiss` (vector store) — not yet installed on this Windows
  machine; `pip install faiss-cpu` when we reach the trading stage.
- yfinance ≥0.2 removed `Adj Close` under default `auto_adjust=True`; `Close` is already
  adjusted. `04_data_pipeline_v2.py` handles this (original would KeyError).

## Open items / gates awaiting user decision

1. **OPENAI_API_KEY is a placeholder in `.env`** — summarization (step 3) and the trading
   stage are blocked until a real key is provided.
2. ~~SEC extraction~~ **DONE 2026-06-12 (user-approved):** all 30 Extractor calls
   succeeded on the first pass (30 of ~100 free credits spent; 0 failures, 0 retries).
   MD&A sections, 27k–67k chars each → `data/01_raw/filing_data.parquet`, schema
   verified against what `04_data_pipeline_v2.py` consumes.
3. **Backbone LLM + split confirmation** — proposal: GPT-4.1, train 2025-01-02→2025-12-31,
   test 2026-01-02→2026-06-01.
4. **Summarization cost estimate** — to be computed from actual TSLA article counts once
   the download finishes, before any OpenAI spend.
