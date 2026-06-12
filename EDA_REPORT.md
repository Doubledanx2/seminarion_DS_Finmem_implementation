# EDA — Model-Input Data (env pickles, verified 2026-06-12)

Window: 2025-01-02 → 2026-06-01 (353 trading days; train sim starts 2025-02-01, test 2026-01-02).
All numbers computed directly from the five validated `data/03_model_input/*.pkl`.

## Corpus & price overview

| Ticker | News in env | Avg/day | Max/day | Zero-news days | Filing days | B&H full window | B&H test window | Ann. vol | Max drawdown |
|---|---|---|---|---|---|---|---|---|---|
| TSLA | 5,262 | 14.9 | 52 | 0 | 6 | +9.6% | **−5.1%** | 57% | −48% |
| NFLX | 1,135 | 3.2 | 40 | **67** | 5 | −3.2% | **−5.6%** | 35% | −43% |
| AMZN | 4,086 | 11.6 | 47 | 0 | 6 | +18.6% | **+15.3%** | 33% | −31% |
| MSFT | 4,002 | 11.3 | 43 | 0 | 6 | +11.3% | **−2.2%** | 27% | −34% |
| COIN | 1,243 | 3.5 | 20 | 24 | 6 | −29.0% | **−22.8%** | 74% | −66% |

## Observations for the presentation

1. **The test window is hostile** — 4 of 5 tickers have negative Buy & Hold in Jan–Jun 2026
   (only AMZN positive). This is a *hard* test for the agent: simply being long loses money
   on most names. Beating B&H here is meaningful; matching it is not embarrassing.
2. **Coverage asymmetry**: TSLA/AMZN/MSFT get ~11–15 articles/day; NFLX and COIN are
   sparse (~3/day) with 67 and 24 zero-news trading days respectively. On zero-news days
   the agent decides from memory + momentum alone → predict per-ticker differences in
   agent behavior (likely more Hold on sparse tickers). Error-analysis angle ready-made.
3. **Volatility spread**: COIN (74%) and TSLA (57%) are the casino; MSFT (27%) the utility.
   Sharpe denominators will differ wildly — report per-ticker, never pooled.
4. **Weekend information loss** (paper-faithful): TSLA 6,146 raw articles → 5,262 in env
   (−14.4%, articles dated Sat/Sun/holidays never reach the agent). Reconciles exactly.
5. **Sentiment format verified**: FinBERT (finbert-tone, B7 label fix) scores appended to
   each summary in the paper's exact prose format ("The positive score for this news is…").
6. **Monthly news counts are stable** (TSLA 215–448/month, no gaps) — no dead months that
   would starve shallow memory.
7. **NFLX price level (~$86-89)** implies a post-2024 stock split reflected in adjusted
   prices — harmless for returns (everything is split-adjusted consistently); noted for
   the corporate-action/adjusted-price caveat in the limitations slide.
8. Filings: 5–6 filing days per ticker in-window (10-K/10-Q summaries land in mid/long
   memory on their EDGAR filedAt dates).

## Open reconciliation item (for Claude Code)

- TSLA summary store shows 3,194 API-summarized rows vs 5,262 env items → confirm the
  remainder (~2,068) are title+summary fallback articles (no body → no API call) and that
  T4 completeness certification counts both paths. AMZN/MSFT/NFLX/COIN stores ≈ full
  article counts, so the fallback share appears TSLA-heavy — verify why.
