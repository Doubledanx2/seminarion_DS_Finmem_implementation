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
| **D20** | 2026-06-12 | **Paper-vs-code discrepancy #3 (after B8 and momentum-3-vs-7): shallow-layer decay.** The repo shipped `[short].recency_factor = 3.0`, but the paper's published value is **Q_shallow = 14** (sensitivity-justified optimum; ARCHITECTURE §4 "decay Q = 14/90/365"). Dan's assistant corrected 3.0 → 14.0 in the TSLA config; propagated to all five gpt41mini configs via the single-source generator. Mid/long (90/365) matched the paper already. Main run uses the paper value; the shipped 3.0 is presentation material |
| ✓ | 2026-06-12 | **STOP #1 cleared: personas APPROVED** (Dan + Claude review, facts verified pre-2025-02). Freeze commit follows |
| B11 | 2026-06-12 | Own-goal during B10 migration: migration wrote ids with isoformat `T` separator while the script built them with a space (`astype(str)`) → resumed run saw ~1.4K done rows as missing and re-summarized them (~180 free-tier requests wasted, $0 billed). Fixed: isoformat everywhere; migration #2 normalized + deduped the store (3,194 unique TSLA rows kept, T4 green). Lesson logged: checkpoint keys need a single canonical serialization |
| D21 | 2026-06-12 | Summarizer 429 handling: exponential backoff 30s→8min (6 attempts, ~15min); persistent 429 now exits **gracefully** (`QuotaExhausted`, checkpoints intact, resume after reset) instead of crashing — first day-1 run died on a 429 wall after 495 requests (TSLA 76% stored at the time) |
| D23 | 2026-06-12 | **Sequential→parallel summarizer (Dan: "why only 20 calls/min?").** Cause: per-request latency ~3s, one request at a time — not a rate limit. 12-way ThreadPoolExecutor (thread-safe meter + store writes) lifted throughput ~12×; TSLA + NFLX completed within minutes of relaunch |
| B12 | 2026-06-12 | Mislabeled abort: a batch with deterministically truncated JSON output (max_output_tokens too tight) burned all 6 retries and raised "QuotaExhausted" though the last errors were parse failures. Fix: `BadBatch` raised after 2 JSON failures (deterministic at temp 0.2), caller **bisects** the batch down to the single poison article → title+summary fallback; output budget +150/item; QuotaExhausted now raised only when the final failures were 429s |
| B13 | 2026-06-12 | T4 env-side trace false-positive: 19 summary texts legitimately recur on multiple dates (republished analyst one-liners) → text→date dict collided, 43 phantom violations (verified: expected-collision count == observed exactly). Test fixed to text→**set of dates**, membership check. Data was correct; no real leakage |
| ✓✓ | 2026-06-12 | **TSLA CERTIFIED end-to-end and TRAIN RUN LAUNCHED** (230 trading days 2025-02-03→2025-12-31, gpt-4.1-mini, frozen f170a92, long-only, as-shipped persona): store complete 6,140/6,140 → env build (353 days) → FinBERT (B7-fixed) → tsla.pkl → MarketEnvironment full-window step → leakage suite ALL PASSED incl. env-side trace (5,262 summaries served on exactly their effective dates). NFLX chain running behind it |
| ✓✓✓ | 2026-06-12 | **TSLA TRAIN RUN COMPLETE** (first full FinMem memory-population run): 229/229 trading days, day-by-day verified (consecutive trading dates in log, weekends skipped; 242 LLM calls ≈ 1.06/day — extras are A1 re-asks). 655K tokens ≈$0.29 list, $0 billed (free pool). **Guardrail failure rate (new metric): 4 re-asks + 1 hold-fallback over 229 days ≈ 2.2%.** Checkpoints: `data/05_train_model_output/TSLA/{agent_1,env}` (~6MB). NFLX→AMZN→MSFT→COIN trains queued sequentially; meter sleeps across 00:00 UTC if pool exhausts |
| **B14** | 2026-06-12 | **Empty-news-day crash (authors' code):** `agent._handling_news` gates on `news != {}` but `news` is a list — `[] != {}` is True, so days with zero articles push an empty list → empty embedding array → `faiss.normalize_L2` IndexError. Invisible on dense tickers (TSLA/AMZN); killed NFLX/MSFT/COIN train runs. Fix: truthiness gate (empty day adds nothing to memory — the intended behavior). Resumed via `sim-checkpoint` from every-step checkpoints |
| B15 | 2026-06-12 | Pre-flight hardening of our own tooling: metrics bootstrap now guards series shorter than the block; pre-flight date scan regex dropped a trailing `\b` (as-shipped prompt glues cur_date to the next sentence — digit→letter has no word boundary, scan saw 0 dates) |
| ✓ | 2026-06-12 | **TSLA TEST pre-flight 15/15 PASS** (Dan's A1–D8; full checklist in STATUS.md). Findings confirmed as-shipped & documented: stray `}` after JSON instructions IS sent to the model; cur_date glued to following sentence. **TSLA TEST RUN STARTED** (103 days 2026-01-02→2026-06-01, trained agent from 05_train_model_output/TSLA, long-only, as-shipped persona) |
| **B16** | 2026-06-12 | **(Dan's directive; he labeled it B15 — renumbered, B15 was taken)** `trading_reflection`'s catch-all exception path returned `{}` silently: the day vanished from the failure-rate metric and produced an implicit no-decision. Now: traceback logged to `validation_events.jsonl` as a fallback event + explicit hold (test) / error record (train). Verified with a simulated transport failure. Note: TSLA's completed runs never hit this path (0 occurrences), so no completed result is affected |
| D24 | 2026-06-12 | Validation-event hygiene: `tests/test_validation.py` ran inside pre-flight subprocesses and wrote its synthetic fixtures (date 2026-01-05) into the production failure log — 20 synthetic rows purged, 12 real kept; `VALIDATION_EVENTS_PATH` env override added so test suites write to a temp file. **Clean production guardrail stats: train — TSLA 4 re-asks/1 fallback (229d), AMZN 3/0 (229d), MSFT 3/0 (partial); test — TSLA 1 re-ask/0 fallbacks (102d)** |
| **F1** | 2026-06-12 | **Error-analysis finding (momentum_agreement metric added to metrics-v2 per Dan):** TSLA test run shows **100% momentum agreement** — 44/44 buys on positive 3-day momentum, 8/8 sells on negative, zero counter-momentum decisions. When not holding, the agent is a pure momentum follower; the memory/reasoning machinery added no directional information beyond the momentum sentence in the prompt. To verify on the other 4 tickers when their tests run — if it generalizes, it's a headline slide |
| **F2** | 2026-06-12 | **CONFIRMED (Stage-5 Task 3): FinMem's deep memory is a revolving door — structurally unable to retain knowledge.** Offline replay of the authors' own per-day dumps (TSLA train, 3,781 memories, 229 days, zero API calls): 176 items ever entered LONG, residence avg/max = **3/3 days**, occupancy ≤7; **zero filings ever reached LONG**. Math: entry bar == exit bar (80) + importance-only decay ⇒ guaranteed expulsion; 10-K direct ingestion (init ≤80) survives ≤1 day; 10-Qs (mid init ≤80, ×0.967) can never promote by decay. Bonus: #3023 recency mystery solved — recency measures time since last *promotion* (delta resets only on up-jump), so frequently-cited items never age (mechanism behind F1's momentum echo). Full report: `DEEP_LAYER_TRACE.md`. Also noted: TSLA's FY2024 10-K (filed 2025-01-30) predates train start by 3 days → never ingested |
| B17 | 2026-06-12 | Cosmetic: `add_memory` ingestion log lines carry no layer header → naive log parsing attributes them to the previous day's last dumped section; identifiable by `rec=1.0, delta=0`. New `MEMORY_EVENT_LOG` instrumentation (Task 3.1: ingest/promote/demote/purge events, env-flagged, OFF in frozen main runs; regression: leakage suite + behavior tests unchanged) supersedes log scraping for future runs |
| D25 | 2026-06-12 | **V-E destination decision (paper-text ambiguity):** paper says insights go to "long-term memory", but LONG would expel them within days (F2) and the shipped code's only agent-text write-path is the reflection layer. Default = **reflection** (conservative, consistent with shipped write-paths); `extended_reflection_target="long"` available by config. V-E module: one call/test-day, M=7 history (decision, reasoning, realized next-day return), contract `{insight, confidence∈low/med/high}`, one re-ask, skip-on-failure. Offline tests 5/5 |
| D26 | 2026-06-12 | `run.py` test mode now applies config overrides for behavior flags onto loaded agents (checkpoint flags otherwise win, so variants could never activate). Main runs unaffected (config == checkpoint flags). **Task 1.1 confirmed:** `paper_rule` = lookback-M=7 PnL sign (same series as get_feedback_response), ≥0→seeking / <0→averse, exact wording from the authors' commented block (`prompts.py`); behavioral tests 2-3 in `test_a4_behaviors.py` cover both the sign rule and the prompt swap |
| **D27** | 2026-06-12 | **Stage 7: "FinMem-Ours" built and FROZEN at `2975839…`** — paper architecture + all our fixes, single headline config. Diffs vs as-shipped (all config-flagged, defaults preserve as-shipped behavior; 6/6 behavior tests + all regression suites green): paper_rule persona with **3-day** switch window (paper §3.1, corrects Stage-5's M=7); extended reflection **both phases → deep layer** (D25 resolved: safe because **downward jumps are disabled** — F2 fix; entry bar ≠ exit bar restores retention); **pure age-based recency** (no reset on promotion — kills the F2 echo-chamber mechanism); observation = **7-day cumulative return** (replaces hardcoded 3d momentum, A4.2); **unit long-only positions {0,+1}**; **ada-002 embeddings** (dim 1536, smoke-tested, ~$1.50 pre-approved); **filing seeding** at sim start with true filedAt (TSLA 10-K 01-29, NFLX 10-K 01-27, MSFT 10-Q 01-29; EDGAR audit: AMZN/COIN have zero filings in the 90d pre-train window — no extra credits); long train window kept (declared deviation from paper's ~72d); personas = approved texts + train-period overview **in test prompts only** (computed from our pickles, Feb–Dec 2025 only — pending Dan's leakage glance) |
| D28 | 2026-06-12 | Quota reallocation per Dan: as-shipped NFLX/AMZN/MSFT/COIN test runs and standalone V-P/V-E runs **cancelled** (superseded by FinMem-Ours); completed TSLA as-shipped train+test kept as the before/after exhibit. Completed as-shipped trains (NFLX/AMZN/MSFT) left on disk, unused. COIN as-shipped train never finished (stopped mid-queue) — irrelevant now |
| D22 | 2026-06-12 | **Gemini key upgraded to PAID tier by Dan** (free-tier daily caps were gating the pipeline by ~2 days). Money gate honored: paid run (~$5–6.50 projected) explicitly approved by Dan ("run it all now"). Script switched to paid-tier mode: pacing 0.2s, request cap lifted, **per-run billed-cost hard abort at $8.00** (Dan's cost-table budget $7.25 +15%); tokens metered during the free-tier era excluded from the billed baseline. Full 5-ticker run launched |

## Stage 8–10 (overnight grid, reporting, deep-dive) — 2026-06-12/13

| # | Date | Entry |
|---|------|-------|
| D29 | 2026-06-13 | **Overnight grid ran unattended and SUCCEEDED**: 5×(train+test) FinMem-Ours + TSLA no-memory + portfolio layer, all 102-day tests, paid overflow used (chat $1.3→$1.66 of the $3 cap). The two POST-PROCESSORS failed: `12_final_report` (BOM) + `13_error_pack` (PYTHONPATH); the orchestrator's `morning_report` then falsely printed "12/12 FULL GRID DONE" because it recomputed run-step predicates and never counted the report steps |
| B18 | 2026-06-13 | **`validation_events.jsonl` had a UTF-8 BOM** (from the B16-era PowerShell `Set-Content -Encoding utf8` dedup) → `12_final_report` `JSONDecodeError`. Fixed: all jsonl reads use `utf-8-sig`; BOM stripped from the file. `13_error_pack` `ModuleNotFoundError: puppy` → pickle.load rebuilds `Portfolio`; added repo-root to `sys.path` |
| B19 | 2026-06-13 | **`morning_report` now truthful**: reads the orchestrator's own `results` dict + real report-artifact predicates (RESULTS has a metric table & no "TEST NOT COMPLETE"; error-pack populated), counts report steps, header = "INCOMPLETE — see failures: …" on any gap; persists `orchestrator_state.json`. Proven both ways (honest INCOMPLETE while stub at 08:30; honest "15/15 FULL GRID DONE" once real). `load_test` completeness predicate keys off the final dir with ≥90 2026 reflections |
| **F3** | 2026-06-13 | **HEADLINE NEGATIVE RESULT — the layered memory hurt.** No-memory ablation (all 5 tickers; same backbone + prompt, retrieval returns empty) mean CR **+12.3%** vs FinMem-Ours **−2.4%** vs B&H **−2.2%** (0bps). Memory hurt or tied on **5/5** (NFLX +57% no-mem vs +19% ours; AMZN +47% vs +24%; TSLA −11% vs −26%; MSFT/COIN ~tied). Ours-vs-no-memory pooled Wilcoxon p=0.13 (median −14 bps/day; not sig. — edge concentrates in a few rally days). FinMem-Ours vs B&H: mean tied, pooled p=0.79; NFLX the one clear win (+19.1%, Sharpe 1.22, break-even 54 bps). Momentum-agreement 100%→74% (behavior changed but didn't help). Pairs with F1/F2 into a coherent "the memory machinery adds cost, not alpha, out-of-sample" story |
| D30 | 2026-06-13 | **Deep-dive evidence** (`14_deep_dive.py` → `DEEP_DIVE*.md`): the FinMem-Ours retention fixes DID work mechanically — TSLA end-state brain holds 1162 memories (vs as-shipped 3-day revolving door), citation share balanced short/mid/long/reflection ≈ 26/22/27/23, and the agent cites its OWN extended reflections (NFLX most-cited memory = a self-reflection, 78×). So the negative F3 result is not "memory never engaged" — it engaged heavily and still didn't help. Cited-id→text resolved from end-state brains (~57%; mid-test purges flagged `[purged]`) |

## Stage 11 — METRICS AUDIT (Sin-4/Sin-5 self-catch) — 2026-06-13

| # | Date | Entry |
|---|------|-------|
| **B20** | 2026-06-13 | **TWO metric bugs found in our own reporting (an independent recompute by Dan disagreed — exactly the "don't trust unaudited backtests" failure mode the project is about).** (1) **Terminal-day truncation:** the report priced on `portfolio.market_price_series`, which ends one decision-day early and **dropped the final test day 2026-06-01 (a −4.57% TSLA day)** — dominant for B&H (claimed TSLA −0.5% vs true **−5.07%**). (2) **Position convention:** `07_metrics_v2.strategy_returns` used the RAW decision as the position (`pos = directions`), so **hold→flat, sell→SHORT** with zero borrow — phantom short profits during declines inflated every strategy cell (NFLX no-mem read **+57%** vs true **+19.8%**, NFLX-Ours +19% vs true **+3.8%**). Both reproduced exactly in `15_reconcile.py` |
| D31 | 2026-06-13 | **Canonical convention adopted** (`16_canonical_metrics.py`, single source of truth): simple daily returns, **carry-forward unit long-only {0,+1}** position (buy=enter/keep, sell=exit, hold=carry) × next-day move, compounded, on the **FULL env price series incl. the terminal day**. Costs = bps×turnover. **Mandatory regression assertion** added: B&H_compound == P[last]/P[first]−1 within 1e-6 per ticker (TSLA −5.07% ✓, all 5 green). `07_metrics_v2.strategy_returns/core_metrics` fixed at source; `12_final_report` rewritten to source from 16; stale `results_finmem_ours.csv` deleted |
| **F3 (revised)** | 2026-06-13 | **Memory-effect finding survives the audit but is much smaller.** Canonical means @0bps: FinMem-Ours **−5.3%**, Buy&Hold **−4.1%**, No-memory **+1.7%**. FinMem-Ours UNDERPERFORMS B&H on the mean; no-memory is the best of the three and beats full FinMem-Ours on **3/5** tickers. Ours-vs-no-mem pooled Wilcoxon p=0.075 (median −28 bps/day; memory hurt, not sig.); Ours-vs-B&H p=0.69. Per-ticker Ours/no-mem/B&H CR0: TSLA −23.1/−5.5/−5.1, NFLX +3.8/+19.8/−5.6, AMZN +15.5/+24.5/+15.3, MSFT −3.9/−6.0/−2.2, COIN −18.5/−24.2/−22.8. As-shipped TSLA canonical −9.2% (was mis-reported −1.9%). **The earlier "+12.3% vs −2.4%" headline was a metrics-bug artifact — corrected, logged, honest.** |
| D32 | 2026-06-13 | **Deck assets rendered** (`17_figures.py` → `data/09_results/figures/`, 17 PNGs: equity ×5, cum-return & Sharpe bars, break-even ×5, NFLX persona timeline, citation share, PCA vector-DB NFLX+TSLA, deep-layer growth vs revolving door; `18_excerpts.py` → `deck_excerpts.md`: 2 reconstructed full prompts, persona quotes, extended reflections, per-ticker biggest-loss-day cited memories + FinBERT sentiment, GitHub-vs-paper discrepancy table). All $0, from artifacts |

## Stage 12 — LC-Trader long-context baseline — 2026-06-13

| # | Date | Entry |
|---|------|-------|
| D33 | 2026-06-13 | **LC-Trader built** (`lc_trader.py`): a plain long-context trader with ZERO FinMem scaffolding — no persona, risk/momentum lines, memory layers, retrieval, FAISS, embeddings, or FinBERT. Each test day sees an append-only context (10-K + latest 10-Q summary, then every day's news summaries ≤ today, our Gemini summaries with sentiment stripped) + a tiny volatile tail (date, position, cum return), and decides buy/sell/hold. Prompt order [SYSTEM][append-only prefix][volatile tail] is byte-identical day-to-day → OpenAI prompt-cache. Canonical accounting (unit long-only, simple, full env series via 16). Leakage assert: max(context date) ≤ cur_date |
| D34 | 2026-06-13 | **Caching worked: 97% cache-hit** on the TSLA run → **$0.78 actual vs $2.82 no-cache (−72%)**, 103 calls, 7.0M input (6.8M cached). **Cost scales ~quadratically with horizon** (append-only context grows linearly toward 135K tokens; cached rate charged on the whole growing prefix daily; last ~40 days hit the 200K TPM limit, auto-retried) — a structural cost FinMem's fixed memory avoids. Pre-run estimate mode projected $2.33 good-cache; actual far lower. Ran TSLA only (Dan: "stop after tesla") |
| **F4** | 2026-06-13 | **LC-Trader (TSLA) finding:** CR **−7.9%** (Sharpe −0.33), decision mix **100 hold / 2 buy / 1 sell** → bought early and basically held (98% days long, turnover 3). It **beats FinMem-Ours (−23.1%)** and tracks near Buy&Hold (−5.1%) / no-memory (−5.5%). So on TSLA, simply streaming the same news into a plain long-context model — with no memory apparatus at all — produced a near-market-tracking passive strategy, while FinMem's full machinery actively traded itself ~15pp below. Strengthens F3: the memory/persona apparatus subtracted value. (TSLA-only; other 4 tickers not run.) Deliverable: `LC_TRADER.md`, folded into `metrics_canonical.{md,csv}` + figures |

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
