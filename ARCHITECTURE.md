# ARCHITECTURE.md — FinMem Reproduction & Extension (Implementation Stage)

MBA LLM-finance seminar · Dan Shoshan & Nimrod Sagi
Reproducing FinMem (Yu et al., arXiv:2311.13743) on a leakage-free 2025–26 window,
plus a portfolio-level extension. This file is the single source of truth for tools,
models, and design decisions. Any deviation requires updating this file + IMPLEMENTATION_LOG.md.

## 1. System overview (mirrors paper Fig. "workflow")

```
                        ┌─────────────────────────────────────────────┐
  Alpaca News API ──►   │  DATA PIPELINE                              │
  SEC EDGAR (10-K/Q) ─► │  summarize (Gemini 3.1 Flash-Lite)          │
  yfinance (prices) ──► │  sentiment (FinBERT, local RTX 3090)        │
                        │  → env_data.pkl per ticker                  │
                        └──────────────┬──────────────────────────────┘
                                       ▼
                        ┌─────────────────────────────────────────────┐
                        │  FINMEM AGENT (×5 tickers, paper-faithful)  │
                        │  Profiling: self-adaptive risk persona      │
                        │  Memory: FAISS, 4 layers                    │
                        │    shallow(news) / mid(10-Q) / deep(10-K)   │
                        │    / reflection — per-layer decay + jumps   │
                        │  Decision: top-K retrieval → gpt-4.1-mini   │
                        │    → guardrails JSON → Buy/Sell/Hold        │
                        └──────────────┬──────────────────────────────┘
                                       ▼
                        ┌─────────────────────────────────────────────┐
                        │  PORTFOLIO LAYER (our extension, NEW)       │
                        │  daily: 5 stock decisions + reasoning →     │
                        │  gpt-4.1-mini → portfolio allocation        │
                        └──────────────┬──────────────────────────────┘
                                       ▼
                        ┌─────────────────────────────────────────────┐
                        │  EVALUATION                                 │
                        │  metrics ± transaction costs, Wilcoxon,     │
                        │  bootstrap CIs, baselines (B&H, no-memory)  │
                        │  → Streamlit replay dashboard               │
                        └─────────────────────────────────────────────┘
```

## 2. Model assignments (FINAL — do not change without user approval)

| Role | Model | Price (in/out per 1M) | Cutoff | Why |
|---|---|---|---|---|
| News/filing summarizer | **Gemini 3.1 Flash-Lite** (`gemini-3.1-flash-lite`) | $0.25 / $1.50 | Jan 2025 | Cheap, 1M ctx; free tier 30 RPM / 1,500 req-day |
| Trading decision (per stock) | **gpt-4.1-mini** | $0.40 / $1.60 | **Jun 2024** | Pre-window cutoff; free via OpenAI data-sharing mini pool (2.5M tok/day @ Tier 1–2) |
| Portfolio-level decision (extension) | **gpt-4.1-mini** | same | Jun 2024 | Same |
| Backbone-sensitivity check | **gpt-4.1**, 1 ticker (TSLA) | $2.00 / $8.00 | Jun 2024 | Measures whether mini-class backbone degrades results |
| Sentiment | **FinBERT** (`yiyanghkust/finbert-tone`, authors' model, B7 label fix), local CUDA | $0 | pre-2021 | Repo-faithful; runs on RTX 3090 |
| Embeddings | **local sentence-transformers on RTX 3090** (e.g., `BAAI/bge-large-en-v1.5`) | $0 | n/a | User decision. Deviation from paper's ada-002 — log as D#; optional ada-002 run costs ≤$1 if fidelity check wanted |

Knowledge-cutoff claim we must be able to make: *every generative model in the pipeline
has a knowledge cutoff before the data window.* Hence train start = 2025-02-01 (clears
Gemini's Jan 2025 cutoff).

## 3. Storage & retrieval

- **Vector store: FAISS** (faiss-cpu is fine; faiss-gpu optional), exactly as in `puppy/memorydb.py`.
  One index per memory layer per ticker. Do not replace with another vector DB.
- Memory mechanics unchanged from the authors' code: compound score = recency
  (per-layer decay Q=14/90/365) + importance + similarity; access-counter promotion
  (jump) between layers; cleanup thresholds as in config.
- If local embeddings are used, dimension changes (1536 → 1024 for bge-large):
  the FAISS index dim is derived from the embedding function — verify `embedding.py`
  & `memorydb.py` handle it; keep the change minimal and logged.

## 4. Experiment design (frozen a priori — anti-cherry-picking)

- **Window:** train 2025-02-01 → 2025-12-31, test 2026-01-02 → 2026-06-01.
  Rationale: entire window postdates every model cutoff (Crime #1 fix).
- **Tickers:** TSLA, NFLX, AMZN, MSFT, COIN (paper's five).
- **Hyperparameters — FROZEN at the paper's published values before any test run:**
  top_k=5, look_back_window_size=7, decay Q = 14/90/365, persona=self-adaptive,
  importance/decay params as in repo configs. No tuning on test data, ever.
  Any sensitivity analysis runs on the TRAIN period only.
- **Baselines:** Buy & Hold (mandatory); no-memory ablation (same backbone + prompt,
  memory module disabled); optional PPO (stable-baselines3, local GPU).
- **Metrics:** Cumulative Return, Sharpe, Max Drawdown, Annualized Vol — each reported
  **with and without transaction costs** (base 10 bps/trade + sensitivity sweep 0–50 bps
  with break-even point). Wilcoxon signed-rank vs. baselines (repo script 08), plus
  moving-block bootstrap 95% CI on Sharpe.
- **Statistical hygiene:** comparisons are few and pre-declared (FinMem vs B&H,
  FinMem vs no-memory, mini vs 4.1). If more are added, apply Bonferroni.

## 5. Software stack

Python 3.10–3.12 · polars/pandas · faiss · guardrails-ai (as pinned by repo) ·
transformers+torch (FinBERT, local embeddings) · openai SDK (>=1.0 — note repo uses
legacy API, adapt the wrapper, not the architecture) · google-genai SDK for Gemini ·
yfinance · stable-baselines3 (optional DRL baseline) · Streamlit (read-only replay
dashboard over checkpoints — built only after results exist).

## 6. Cost & quota plan

See cost table in claude_code_prompt_02_implementation.md. Hard rules:
estimate before any paid run; respect free-tier daily quotas (Gemini 1,500 req/day;
OpenAI data-sharing mini pool 2.5M tok/day, resets 00:00 UTC); checkpoint-resume
across days is the default mode of operation; a per-run token/cost meter is mandatory.
