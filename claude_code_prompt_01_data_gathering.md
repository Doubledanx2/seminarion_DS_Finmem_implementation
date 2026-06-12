# Prompt for Claude Code — Stage 1: Data Gathering

Copy everything below the line into Claude Code, run from the repo root.

---

## Context

This is an MBA data-science seminar project. We are reproducing **FinMem** (Yu et al., "FinMem: A Performance-Enhanced LLM Trading Agent with Layered Memory and Character Design", arXiv:2311.13743). This repo is the authors' original codebase. We already gave the 45-minute paper presentation; we are now in the **implementation stage**: reproduce the system, run our own experiments, and present results in a 30-minute implementation presentation that must include experimental design, leakage avoidance, baselines, and error analysis.

Read these before doing anything:

- `README.md` — repo overview and run instructions
- `data-pipeline/README.md` — the full data pipeline documentation (this stage's bible)
- `run.py` — entry point; shows what the model expects as input (`env_data.pkl` per ticker in `data/03_model_input/`)
- `config/tsla_gpt_config.toml` — config format
- `data-pipeline/01_Alpaca_News_API_download.py`, `01_SEC_API_10k10q_download.py`, `03-model_wrapper.py`, `03-summary.py`, `04-data_pipeline.py`, `05-get_sentiment_by_ticker.py` — the pipeline scripts you'll be running/adapting

**Critical background — why our dates differ from the paper:** In our paper presentation we identified pre-training leakage as the paper's biggest flaw: their test window (Oct 2022 – Apr 2023) sits **inside** GPT-4-Turbo's training data, so the model may simply "remember" Tesla's 2022 crash rather than predict it. Our fix: run the entire experiment on a **recent window that postdates the backbone LLM's knowledge cutoff**. This is the centerpiece of our experimental design — do not silently revert to the paper's dates.

## Objective

Build the complete model-input dataset for all 5 tickers from the paper — **TSLA, NFLX, AMZN, MSFT, COIN** — using the **same sources the paper used**:

1. **News:** Alpaca News API (historical news endpoint)
2. **Filings:** SEC 10-K and 10-Q via sec-api.io (as in `01_SEC_API_10k10q_download.py`)
3. **Prices:** Yahoo Finance via `yfinance` (adjusted close), handled inside `04-data_pipeline.py`

## Date window

- **Full data window:** 2025-01-01 → 2026-06-01
- **Proposed split (confirm with me before finalizing):** train 2025-01-02 → 2025-12-31, test 2026-01-02 → 2026-06-01
- Before locking the split, verify the knowledge cutoff of the backbone LLM we'll use for trading (paper used GPT-4-Turbo; we'll use the closest currently-available equivalent). The **test window must lie entirely after that cutoff**. Report what you find and flag any problem.

## Pipeline steps (follow `data-pipeline/README.md`)

1. **Download news** per ticker from Alpaca (full window). Keys are in `.env` as `ALPACA_KEY` and `ALPACA_KEY_SECRET_KEY` (the exact names `01_Alpaca_News_API_download.py` reads). If keys are missing, stop and ask me.
2. **Download 10-K/10-Q** for the 5 tickers covering the window via sec-api.io (`SEC_KEY` in `.env`, as `01_SEC_API_10k10q_download.py` expects). The free tier has only ~100 credits and the Extractor API costs one call per section — plan the exact number of calls needed, report it to me, and get approval BEFORE running. If quota is insufficient, propose a fallback (free SEC EDGAR download + local parsing) and wait for my decision.
3. **Summarize** news and filings using the **same model family the paper used for trading decisions (GPT-4-Turbo class)** via `03-model_wrapper.py` (rename to `model_wrapper.py` as the README instructs) + `03-summary.py`. Use `OPENAI_API_KEY` from `.env`. **Before the full run, estimate the total token cost and report it to me for approval.** If cost is excessive, propose a cheaper model and we'll decide together.
4. **Run `04-data_pipeline.py`** to produce `price.pkl`, `news.pkl`, `filing_q.pkl`, `filing_k.pkl`, `env_data.pkl`.
5. **Sentiment:** run `05-get_sentiment_by_ticker.py` with **FinBERT** (what the paper used).
6. **Final outputs:** one model-input pickle per ticker at `data/03_model_input/<ticker>.pkl`, in exactly the structure `run.py` / `puppy/environment.py` expects. Verify by loading each pickle and stepping a `MarketEnvironment` through a few days.

## Constraints & expectations

- The pipeline scripts are research code (hardcoded paths, renamed imports, possibly stale API usage). Fix what's broken, but keep changes minimal and documented — we must report "implementation challenges" in our presentation. Keep a running log of every bug/fix/decision in `IMPLEMENTATION_LOG.md` at repo root.
- Alpaca news may be sparse for some tickers/dates — report per-ticker article counts per month so we can spot gaps.
- COIN note: in the paper, COIN was a recent IPO with no DRL training history. In our 2025–26 window it has years of history — note this in the log; it changes the baseline story.
- Don't run the trading simulation yet — this stage is data only.
- Work incrementally: validate one ticker (TSLA) end-to-end first, get my sign-off, then fan out to the other four.
- Python 3.10, deps in `pyproject.toml` / `.devcontainer/requirements.txt`.

## Deliverables

1. `data/03_model_input/{tsla,nflx,amzn,msft,coin}.pkl` — validated
2. `IMPLEMENTATION_LOG.md` — every issue, fix, decision, and data-quality observation
3. A short summary: article counts per ticker, filings retrieved, total API cost spent, and any data-quality concerns
