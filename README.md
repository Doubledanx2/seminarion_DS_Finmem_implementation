# Reproducing FinMem on a Leakage-Free Window — MBA Data-Science Seminar

**Dan Shoshan & Nimrod Sagi** · reproduction and critical assessment of
Yu et al., *FinMem: A Performance-Enhanced LLM Trading Agent with Layered Memory and
Character Design* ([arXiv:2311.13743](https://arxiv.org/abs/2311.13743)).

This repository builds on the authors' original code (credited below) and re-runs the
whole experiment on a **leakage-free 2026 test window** that postdates every model's
knowledge cutoff — the fix for the paper's central flaw, where its 2022–23 test window
sat inside the backbone LLM's training data.

## Headline result (test 2026-01-02 → 2026-06-01, 5 tickers)

On out-of-sample data the layered-memory + persona apparatus **did not add value** — it
was beaten by simpler baselines:

| Strategy | Mean cumulative return (0 bps) | Mean Sharpe |
|---|---|---|
| No-memory ablation | **+1.7%** | +0.38 |
| LC-Trader (plain long-context) | −2.9% | +0.16 |
| Buy & Hold | −4.1% | +0.11 |
| **FinMem-Ours** (full apparatus) | **−5.3%** | −0.15 |

Full numbers: [`RESULTS_FINMEM_OURS.md`](RESULTS_FINMEM_OURS.md) and
[`data/09_results/metrics_canonical.md`](data/09_results/metrics_canonical.md). The detailed
development report is the submission PDF (`IMPLEMENTATION_DEVELOPMENT.pdf`).

## What's here

```
puppy/                 the FinMem agent (memory DB, reflection, chat, portfolio) — our fixes applied
config/                per-ticker TOML configs; *_finmem_ours_config.toml is the frozen "FinMem-Ours"
data-pipeline/         numbered pipeline: 00–05 data prep, 12/16 metrics, 14 deep-dive, 17–22 figures
lc_trader.py           the plain long-context baseline (no FinMem machinery)
run.py                 train/test runner (the paper's simulation loop)
run_overnight.py       unattended orchestrator (checkpoint-resume, cost caps)
tests/                 leakage (T1–T4) + behaviour test suites
ARCHITECTURE.md        binding design decisions          IMPLEMENTATION_LOG.md  every bug/decision/finding
RESULTS_FINMEM_OURS.md results narrative                 DEEP_DIVE_*.md         per-ticker decision/memory analysis
DEEP_LAYER_TRACE.md    the deep-memory "revolving door" finding   EDA_REPORT.md   data overview
```
*(The `data/` folder — news, summaries, model-input pickles, trained agents, results,
figures — is excluded from the code submission; everything is regenerable, see below.)*

## How to run

Python 3.10–3.12.

```bash
pip install -r requirements.txt      # all dependencies, pinned
cp .env.example .env                 # then fill in your own API keys
```

API keys go in `.env` (see `.env.example` for the exact names: `OPENAI_API_KEY`,
`GEMINI_API_KEY`, `ALPACA_KEY` / `ALPACA_KEY_SECRET_KEY`, `SEC_KEY`). **No keys are
included in this submission.** Regenerating the metrics and figures from the saved
checkpoints needs neither keys nor a GPU; keys are only needed to re-run the data
pipeline and the train/test LLM calls.

```bash
# 1. data pipeline (news, filings, summaries, sentiment -> data/03_model_input/<ticker>.pkl)
python data-pipeline/01_alpaca_news_download_v2.py
python data-pipeline/01_sec_10k10q_download_v2.py
python data-pipeline/03_summarize_gemini_v3.py news
python data-pipeline/05_sentiment_v2.py
python data-pipeline/04_data_pipeline_v2.py

# 2. train + test one ticker (FinMem-Ours, frozen config)
python run.py sim -mdp data/03_model_input/tsla.pkl -st 2025-07-01 -et 2025-12-31 -rm train \
   -cp config/tsla_finmem_ours_config.toml -ckp data/06_train_checkpoint/TSLA_ours -rp data/05_train_model_output/TSLA_ours
python run.py sim -mdp data/03_model_input/tsla.pkl -st 2026-01-02 -et 2026-06-01 -rm test \
   -cp config/tsla_finmem_ours_config.toml -ckp data/08_test_checkpoint/TSLA_ours \
   -rp data/07_test_model_output/TSLA_ours -tap data/05_train_model_output/TSLA_ours

# 3. baselines + audited metrics + figures (no model spend; reads checkpoints)
python lc_trader.py run                      # long-context baseline (all tickers)
python data-pipeline/16_canonical_metrics.py # -> metrics_canonical.{md,csv}
python data-pipeline/17_figures.py           # -> data/09_results/figures/
```

All metrics use one **canonical convention** (long-only unit positions, simple compounded
returns on the full price series including the final test day), enforced by an assertion in
`16_canonical_metrics.py`. Leakage tests: `python tests/test_leakage.py`.

## Credit

Original code and method: Yu et al. (Stevens Institute of Technology),
<https://github.com/pipiku915/FinMem-LLM-StockTrading>. Licensed MIT (see `LICENSE`). Our
contribution is the leakage-free re-run, the corrected/extended **FinMem-Ours**
configuration, the no-memory and long-context baselines, the audited metrics, and the
critical assessment documented across the `*.md` reports.
