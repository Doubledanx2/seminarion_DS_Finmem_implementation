# Prompt for Claude Code — Stage 2: Pipeline Completion + Simulation

Copy everything below the line into Claude Code, run from the repo root.

---

## Context

Continue the FinMem reproduction (Stage 1 = news download, complete). Before anything
else, read in this order:

1. `ARCHITECTURE.md` — final tool/model decisions. Binding.
2. `BACKTEST_INTEGRITY.md` — Seven Sins checklist. Binding; treat as a test suite.
3. `IMPLEMENTATION_LOG.md` — what happened in Stage 1.
4. `STATUS.md` — your live snapshot file; the spec is in its header comment.
5. `data-pipeline/README.md`, `puppy/` source, `config/*.toml` (you know these).

All previously open gates are now DECIDED:

- **Summarizer = Gemini 3.1 Flash-Lite** (cutoff Jan 2025). `GEMINI_API_KEY` will be in `.env`.
- **Decision model = gpt-4.1-mini** (cutoff Jun 2024), for both per-stock agents and the
  portfolio layer. Use the OpenAI data-sharing free pool (2.5M tokens/day, mini models,
  resets 00:00 UTC) when available; otherwise standard paid calls.
- **Window: train 2025-02-01 → 2025-12-31, test 2026-01-02 → 2026-06-01.**
  (Train start moved from Jan to Feb to clear Gemini's Jan-2025 cutoff.)
- **SEC extraction: APPROVED.** ~30 sec-api Extractor credits (10-K item 7, 10-Q part1item2),
  filing index from free EDGAR. Index by **filedAt**, never period-of-report.
- **Embeddings: local on the RTX 3090** (`BAAI/bge-large-en-v1.5` via sentence-transformers,
  CUDA). Log the dimension change vs ada-002 as a deviation. Keep an ada-002 code path
  switchable by config.
- **Sentiment: FinBERT local.**
- **Hyperparameters FROZEN** per ARCHITECTURE.md §4 (top_k=5, M=7, paper decay rates,
  self-adaptive persona). Commit this state to git before the first test run and record
  the hash in STATUS.md.
- **Shorting: long-only main run** — "Sell" closes the position to flat, never opens a
  short (BACKTEST_INTEGRITY.md Sin 7). Implement as a config flag so the paper's
  long-short behavior remains available as a secondary run.

## Work plan (validate TSLA end-to-end at each stage before fanning out)

1. **SEC filings** → summarize → into pipeline. Report credits used in STATUS.md.
2. **Summarization** of all news (Gemini 3.1 Flash-Lite). Batch multiple articles per
   request where quality allows; fall back to title+summary for body-less articles
   (~15–30% are analyst one-liners — title IS the content). Free tier first
   (30 RPM / 1,500 req/day), paid overflow only after reporting projected cost.
   Run a 50-article quality sample and show me examples BEFORE the full run.
3. **Sentiment + env_data assembly** (fix the known `filling_`/`filing_` key bug and the
   tuple-vs-dict mismatch noted in the log; original files stay untouched — work in v2
   scripts as established).
4. **Leakage unit test** (Sin 2): step MarketEnvironment over the full window asserting
   no future-dated content is ever served. Must pass before any LLM run.
5. **Adapt `chat.py`** minimally: gpt-4.1-mini via current openai SDK; token/cost meter
   on every call; daily-quota-aware pacing with checkpoint-resume across the 00:00 UTC
   reset (the repo already checkpoints every step — use it).
6. **Train runs** (memory population, 5 tickers) → **test runs**. One LLM call per
   ticker-day, guardrails num_reasks=1 (unchanged).
7. **Portfolio layer (our extension):** after the 5 per-stock decisions each test day,
   one gpt-4.1-mini call takes the 5 decisions + reasoning + current portfolio state and
   outputs target weights (long-only, sum ≤ 1, cash allowed). Log reasoning. Keep the
   prompt simple and fixed; this is new code, isolate it in its own module.
8. **Baselines:** Buy & Hold per ticker + equal-weight portfolio; no-memory ablation
   (same backbone/prompt, memory retrieval returns empty). Optional if time: PPO via
   stable-baselines3 on the 3090.
9. **gpt-4.1 TSLA fidelity run** (~$3) — only after the mini main run completes.
10. **Metrics:** with/without 10 bps costs + 0–50 bps sweep with break-even, Wilcoxon,
    moving-block bootstrap CI on Sharpe, top-5-day contribution, per-month returns.
    Extend `07-metrics.py` ideas into a v2 metrics module.
11. **Streamlit replay dashboard** — read-only over checkpoints/logs: date scrubber,
    per-layer retrieved memories, persona state, reasoning chain, action, equity curve,
    portfolio weights. No live API calls.

## Operating rules

- STATUS.md: overwrite after every completed step or new blocker (spec in file header).
- IMPLEMENTATION_LOG.md: append every bug/fix/decision (continue Stage-1 numbering).
- Money gates: report projected cost and STOP for approval before any paid run
  > $2, and before exceeding 50 sec-api credits total.
- Never tune anything on test data. If you are tempted, write it in STATUS.md as a
  question instead.
- BACKTEST_INTEGRITY.md boxes: check them off as you implement, in STATUS.md.

## Cost reference (estimates, verified 2026-06-12)

| Item | Model | Tokens (est.) | Paid cost | Free-tier path |
|---|---|---|---|---|
| Summarization (18.3K articles + 30 filings) | Gemini 3.1 Flash-Lite $0.25/$1.50 | ~14M in / 2.5M out | ~$7.25 | $0 over ~3 days (batched, 1,500 req/day) |
| Stock decisions (5 × ~229 train + ~104 test days) | gpt-4.1-mini $0.40/$1.60 | ~5.0M in / 0.33M out | ~$2.55 | $0 over ~2–3 days (2.5M/day mini pool) |
| Portfolio layer (~104 test days) | gpt-4.1-mini | ~0.25M in / 0.04M out | ~$0.16 | same pool |
| Embeddings | bge-large, local 3090 | — | $0 | — |
| Sentiment | FinBERT, local | — | $0 | — |
| gpt-4.1 TSLA fidelity run | gpt-4.1 $2.00/$8.00 | ~1.0M in / 0.07M out | ~$2.60 | partially offset by 250K/day big pool |
| SEC extraction | sec-api free credits | 30 calls | $0 | — |
| **Total** | | **~22M** | **~$12.50 max** | **~$2.60 with free tiers** |

+15% contingency for guardrails re-asks and retries. All spend logged in STATUS.md meters.
