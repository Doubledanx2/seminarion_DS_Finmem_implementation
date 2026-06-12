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

## Stage 2 (started 2026-06-12)

| # | Date | Entry |
|---|------|-------|
| D6 | 2026-06-12 | Stage-2 binding decisions adopted from ARCHITECTURE.md: Gemini 3.1 Flash-Lite summarizer, gpt-4.1-mini decisions, train window now **2025-02-01**→2025-12-31 (clears Gemini's Jan-2025 cutoff), local bge-large embeddings, long-only main run |
| D7 | 2026-06-12 | Summarizer design (`03_summarize_gemini_v3.py`): batches ≤8 articles / ≤24k chars per request with JSON-schema array output; articles with <400 chars total text skip the API (title+summary IS the summary — analyst one-liners); 30 RPM pacing + 1,450 req/run budget with jsonl checkpoint-resume across the 00:00 UTC free-tier reset; persistent token/cost meter |
| D8 | 2026-06-12 | Filings summarized to ≤400 tokens each (MD&A → trading-agent brief); output `filing_data_summarized.parquet`, same schema, so `04_data_pipeline_v2.py` consumes either raw or summarized transparently |
| T1 | 2026-06-12 | **Sin-2 leakage unit test written and PASSING** (`tests/test_leakage.py`): news dates only move forward (≤1 day, 16:00 rule); filings keyed by acceptance/filedAt (TSLA FY2025 10-K lands 2026-01, not in-period); MarketEnvironment steps 353 days strictly increasing. Item-level news tracing activates once summary CSVs + final pickles exist |
| — | 2026-06-12 | Installed google-genai 2.8.0 (httpx bumped 0.27→0.28, no breakage) and faiss-cpu 1.14.2 (stage-7 prep) |
| **B7** | 2026-06-12 | **Substantive bug in authors' sentiment code:** `yiyanghkust/finbert-tone` id2label is `{0: Neutral, 1: Positive, 2: Negative}`, but `05-get_sentiment_by_ticker.py` reads `pos=scores[2], neu=scores[1], neg=scores[0]`. The paper's "positive score" injected into agent memory was actually **P(Negative)** (and "negative" was P(Neutral)). Our `05_sentiment_v2.py` maps by label *name* (`model.config.id2label`), robust to any FinBERT variant. Presentation-worthy: the paper's reported results were obtained with scrambled sentiment annotations |
| D9 | 2026-06-12 | Local embedding backend added (`puppy/embedding.py::LocalSentenceTransformerEmb` + `make_embedding_function` factory; one-line change in `memorydb.py`). `backend="local"` → bge-large-en-v1.5 on CUDA (dim 1024); `backend="openai"` (default) → original ada-002 path preserved. langchain import made lazy so the local path doesn't require it |
| D10 | 2026-06-12 | `chat.py` adapted: `TokenMeter` (persistent per-UTC-day token/cost meter, json on disk) + daily-quota awareness — sleeps until 00:05 UTC or raises `DailyQuotaExhausted` per config (`daily_token_budget`, `wait_for_reset` in `[chat]`); non-API keys filtered out of the request payload (original leaked `tokenization_model_name` into it). Legacy raw-HTTP call path kept (still valid against current OpenAI API) |
| T2 | 2026-06-12 | Local model stack smoke test green (`tests/test_local_models.py`): bge-large 1024-dim on the RTX 3090, FAISS IndexIDMap2 roundtrip ranks TSLA-delivery docs first, FinBERT label-corrected scoring (clearly-positive sentence → pos=1.0; under the original mapping it would have read pos=0.0) |
| D11 | 2026-06-12 | `config/tsla_gpt41mini_config.toml` created (frozen hyperparams per ARCHITECTURE §4). Removed the persona's hardcoded 2021-22 Tesla performance recap — false in our window and itself mild leakage |
| Q1 | 2026-06-12 | ~~Open question~~ **Resolved by addendum A2: finbert-tone** (authors' actual model) with the B7 name-based label fix; ARCHITECTURE.md §2 updated |
| D12 | 2026-06-12 | **A1 executed:** guardrails-ai 0.3.2 (needs py<3.11) replaced by `puppy/validation.py` — same validation contract (decision ∈ buy/sell/hold, cited memory ids ∈ retrieved list, ONE re-ask carrying the failed output + error, persistent failure → train error-record / test hold). `reflection.py` rewired (guardrails pydantic factories removed, prompt JSON-instruction now explicit incl. allowed ids per layer). Every re-ask/fallback appended to `data/04_model_output_log/validation_events.jsonl` → **guardrail failure rate** reportable per model — new metric the paper never measured (quantifies hidden Hold bias). Contract test 5/5 green offline (`tests/test_validation.py`); `puppy` imports cleanly on Python 3.12 |
| T3 | 2026-06-12 | **Gemini quality sample (50 articles, 7 batched requests, ≈$0.02 list / $0 free-tier):** summaries concrete (numbers, analyst actions, price targets, dates preserved); batching at 8 articles/request holds quality. Review file `data/02_intermediate/gemini_quality_sample.md`. Observation: many ticker-tagged articles are market-roundups where the ticker is incidental — Gemini still extracts the ticker-relevant facts |
| T4 | 2026-06-12 | **A3 canary green:** 10 gpt-4.1-mini calls through the production path (`chat.py` guardrail endpoint + TokenMeter): 10/10 valid JSON decisions, 17,988 in / 449 out tokens. STOPPED per A3 — Dan must verify $0.00 billed on platform.openai.com/usage before any real run |
| D13 | 2026-06-12 | Full-summarization projection from real data: 14,551 articles need the API (~1,819 batched requests), 3,760 are body-less → free title+summary fallback (20.5%), +30 filings ⇒ ~1,849 requests ≈ 2 free-tier days ($0; fully-paid worst case ~$6) |
| D14 | 2026-06-12 | **A5 compliance retrofit of the summarizer** (first sample predated A5). Prompt diff: (a) articles now ID-tagged (`=== ARTICLE id=A1 ===`) and output parsed **per-ID** as `[{id, summary}]` with completeness check, was positional JSON array; (b) added strict isolation rules — "use ONLY the text of that article, no background knowledge, no added context, no cross-article influence" (A5.2/A5.5), was absent; (c) summary store rows now carry the full A5.1 schema `(article_id, symbol, source_datetime_utc, effective_trading_date, summary, model, tokens)` with both dates taken from our pipeline columns, was `(url, summary, how)`; (d) filings keyed by filedAt EST date, same schema (A5.3); (e) batch token usage split evenly across batch items (documented approximation). 20-article regen sample: `gemini_quality_sample_v2_a5.md` — spot review found **no model-injected context** (all summary facts traceable to source text); flagged for Dan's final eyeball per A5.5 |
| ✓ | 2026-06-12 | **Dan gate results:** canary $0.00 billed confirmed (free pool active) → OpenAI GO; summarization GO conditional on A5 re-validation (done above). Full Gemini run launched (filings 30 req + news, day 1 of ~2, checkpointed) |
| **B8** | 2026-06-12 | **Verified (A4.1): self-adaptive persona is NOT in the shipped code.** The two-sided rule exists only as comments (`prompts.py:39-40`); the shipped test prompt carries one static, *unconditional* "you are a risk-seeking investor" line; grep over `puppy/` finds no other injection path. Implemented config flag `persona_rule = "as_shipped"` (default, main result) vs `"paper_rule"` (ablation): paper_rule swaps the line for the authors' own commented two-sided sentence chosen by the sign of the portfolio's lookback cumulative PnL (`Portfolio.get_lookback_risk_state()`; early days → seeking, matching "positive or zero"). Behavioral test green |
| D15 | 2026-06-12 | **A4.2 momentum documentation (no behavior change):** `moment_window=3` is hardcoded at `agent.py:297` and feeds only the TEST-mode prompt's momentum sentence. `look_back_window_size=7` (config) feeds `Portfolio.get_feedback_response()` — the 7-day PnL sign used as feedback for memory access-counter reinforcement (train and test). Two different windows for two different signals; paper text conflates them |
| D16 | 2026-06-12 | **A4.4 long-only (Sin 7):** `Portfolio(long_only=True)` clamps `holding_shares ≥ 0` ("Sell" closes to flat, never shorts); the RAW decision still goes to `action_series`, so the direction-based primary metric is unaffected and the paper's long-short path stays intact via `long_only=false`. Flag in `[general]`, persisted through agent checkpoints |
| D17 | 2026-06-12 | **A3.2 hard budget guard:** `TokenMeter.check_budget` now (a) raises `BudgetExhausted` when lifetime worst-case projected spend ≥ $4.00, (b) refuses to *start* any request within 16K tokens of the daily free quota (overflowing requests bill in full) — sleeps to 00:05 UTC or raises per config. Behavioral tests green |
| B9 | 2026-06-12 | Original `TextTruncator.truncate_text` calls `self.tokenize_cnt_texts` — method doesn't exist (missing underscore) → would AttributeError on first use. Fixed alongside **A4.6**: gpt-* tokenization now via tiktoken (`encoding_for_model`, fallback `o200k_base`); HF path unchanged for non-gpt; removed the gpt early-return that returned a bare list where callers expect a (list, count) tuple |
| D18 | 2026-06-12 | **A4.5 sampling params:** as-shipped payload sends NO sampling params → OpenAI defaults (temperature=1.0, top_p=1.0). Pinned `temperature = 1.0` explicitly in all five configs (identical behavior, now documented); single-run nondeterminism noted — one run per configuration per Sin 4, no seed-shopping |
| D19 | 2026-06-12 | **A4.3 personas authored** for all 5 tickers (`config/{tsla,nflx,amzn,msft,coin}_gpt41mini_config.toml`, generated single-source from the TSLA template by `00_make_ticker_configs.py`): sector-expertise lists + business-fact paragraphs using ONLY pre-2025-02 facts (latest fact: spot-BTC-ETF custody, Jan 2024); no performance recaps, no forward-looking claims. **A4.7 verified in the same script: top_k=5 + exact model string in all five.** STOPPED for Dan & Nimrod's review per plan |
| **B10** | 2026-06-12 | **Found via our own T4 test: Alpaca article URLs are NOT unique** — `benzinga.com/quote/TSLA` is shared by 7 distinct articles; keying the A5.1 store by bare URL silently dropped 6 of them and produced 1 date mismatch. Fix: `article_id = url#source_datetime_utc`; existing 1,471 TSLA rows migrated in place (0 ambiguous, backup kept); T4 now PASSES (1,471 news + 30 filing rows date-exact). The colliding articles get summarized fresh under unique ids |
| T5 | 2026-06-12 | **T4 (A5.4) added to `tests/test_leakage.py`** — summary-store dates must equal pipeline-effective dates (news) / filedAt EST (filings); env-side trace (served summary's date == cur_date) activates when final pickles exist. Suite: ALL CHECKS PASSED |

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
