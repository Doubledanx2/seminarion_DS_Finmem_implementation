# BACKTEST_INTEGRITY.md — Seven Sins Checklist for This Project

Source: Luo et al. (2014) "Seven Sins of Quantitative Investing" + course compendium on
backtesting methodology. Every item below must be either implemented or explicitly
disclosed as a limitation in the implementation presentation. Claude Code: treat this
as a test-suite for the experiment design; check items off in STATUS.md.

## Sin 1 — Survivorship bias
**Exposure: HIGH, inherited from the paper.** The 5 tickers are hand-picked surviving
mega-caps; no delisted assets in the universe.
- [ ] Cannot fully fix (paper replication) → DISCLOSE on limitations slide: results
      estimate "FinMem on stocks that survived", not "FinMem on the market".
- [ ] Do not generalize conclusions beyond the 5-ticker universe anywhere in the report.

## Sin 2 — Look-ahead bias  ← our headline fix
**Exposure: was the paper's central flaw (LLM pre-training leakage).**
- [ ] All model cutoffs precede the data window (gpt-4.1-mini Jun-2024, Gemini Jan-2025;
      train starts 2025-02-01). Verify and record each cutoff in STATUS.md.
- [ ] Dual timestamps for filings: index 10-K/10-Q by **filedAt (publication date)**,
      never by period-of-report. Verify in pipeline output.
- [ ] News after 16:00 ET attributed to the next trading day (paper's rule — keep).
- [ ] Prices: yfinance auto-adjusted close used consistently; note the (minor)
      retroactive-adjustment caveat in the log.
- [ ] No data from after a simulated day reaches the agent on that day — assert in a
      unit test that steps through MarketEnvironment and checks max(news_date) ≤ cur_date.

## Sin 3 — Storytelling
**Exposure: MEDIUM — error analysis invites post-hoc narratives.**
- [ ] Hypotheses and frozen hyperparameters are committed (git, dated) BEFORE the first
      test run. The commit hash goes on the methods slide.
- [ ] In error analysis, label every interpretation of agent behavior as observation vs.
      speculation. LLM reasoning chains are themselves stories — audit them against the
      actual retrieved memories (did the cited memory IDs really support the decision?).

## Sin 4 — Data mining / snooping  ← Crime #3 fix
**Exposure: was the paper's flaw ("highest cumulative return setting" reported).**
- [ ] Zero test-set tuning. Hyperparameters = paper's published values, frozen in
      ARCHITECTURE.md §4.
- [ ] Pre-declared comparison list only; Bonferroni if it grows.
- [ ] One run per configuration (no seed-shopping). If variance is studied, report ALL runs.

## Sin 5 — Transaction frictions  ← Crime #2 fix
**Exposure: was the paper's flaw (zero-friction reward in 07-metrics.py).**
- [ ] All headline metrics reported with AND without costs; base case 10 bps/trade.
- [ ] Sensitivity sweep 0–50 bps; report the break-even cost where FinMem's edge over
      Buy & Hold disappears. (FinMem trades daily → high turnover → this number matters.)

## Sin 6 — Outliers
**Exposure: MEDIUM — single path, 5 tickers, meme-y stocks (TSLA, COIN).**
- [ ] Report top-5 winning/losing days' contribution to cumulative return per ticker.
      If a handful of days drive the result, say so.
- [ ] Report median daily return alongside mean; moving-block bootstrap 95% CI on Sharpe.

## Sin 7 — Asymmetric payoffs / shorting constraints
**Exposure: HIGH and NOT in our original three crimes — new finding from this review.**
The repo's portfolio (`puppy/portfolio.py`) allows "Sell" to open/hold SHORT positions
with zero borrow fees, no hard-to-borrow constraint, no margin, no recall risk. TSLA and
COIN are historically expensive borrows.
- [ ] Decide and implement ONE of: (a) long-only/flat interpretation of Sell (close
      position, never short), reported as main result, with the paper's long-short as a
      secondary run; or (b) keep long-short but add a borrow-fee haircut sensitivity.
      Recommendation: (a) — defensible and simple.
- [ ] Either way, disclose the paper's frictionless-shorting assumption as Crime #4 on
      the critical-assessment slide.

## Beyond the Sins (compendium ch. 2, 4, 5)
- [ ] **Single-path fallacy / regime dependence:** our test window (Jan–Jun 2026) is one
      regime. Disclose; report per-month returns so regime sensitivity is visible.
      (Optional stretch: block-bootstrap synthetic paths for the final portfolio.)
- [ ] **Perfect-backtest smell test:** if any configuration produces Sharpe > 2, treat it
      as a red flag and audit before celebrating — exactly what we told the paper's authors.
- [ ] **Challenger principle (human oversight):** never report only aggregates. The
      Streamlit replay exists so we inspect raw reasoning chains and raw daily decisions,
      not just the equity curve. Sample ≥20 random agent-days per ticker for manual review.
