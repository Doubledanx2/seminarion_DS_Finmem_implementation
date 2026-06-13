# RESULTS — FinMem-Ours (audited, canonical) · test 2026-01-02 → 2026-06-01

> ⚠️ **Corrected metrics (Stage-11 audit).** Earlier builds of this file used raw decisions as the position (hold=flat, sell=SHORT) + log returns, which created phantom short profits and inflated every cell (e.g. NFLX no-mem read +57% vs the true +20%, NFLX-Ours +19% vs the true +3.8%). All numbers below use the canonical convention: **carry-forward unit long-only {0,+1} × simple next-day return, compounded, on the full env price series.** Full table: `data/09_results/metrics_canonical.{md,csv}`; reconciliation: `15_reconcile.py`.


## TSLA

| | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |
|---|---|---|---|---|
| Cum. return | -23.1% | -25.5% | -5.1% | -5.5% |
| Sharpe | -1.92 | -2.17 | -0.14 | -0.37 |
| Sortino | -2.57 | | -0.25 | |
| Max drawdown | -30.2% | -31.9% | -24.0% | |

Ann.vol 31% · alpha(ann) -56.6% · beta 0.65 · turnover 31 · 54% days long
Decisions: 49 buy / 11 hold / 42 sell · momentum-agreement 73% (n=89) · guardrails: 6 re-asks / 0 fallbacks
Per-month (10bps): 2026-01 -10.4%, 2026-02 -6.5%, 2026-03 -9.5%, 2026-04 -0.5%, 2026-05 -1.2%

## NFLX

| | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |
|---|---|---|---|---|
| Cum. return | +3.8% | +1.9% | -5.6% | +19.8% |
| Sharpe | 0.44 | 0.30 | -0.19 | 1.56 |
| Sortino | 0.48 | | -0.30 | |
| Max drawdown | -15.4% | -15.9% | -20.7% | |

Ann.vol 34% · alpha(ann) +20.8% · beta 0.81 · turnover 18 · 55% days long
Decisions: 48 buy / 28 hold / 26 sell · momentum-agreement 77% (n=71) · guardrails: 0 re-asks / 0 fallbacks
Per-month (10bps): 2026-01 -5.8%, 2026-02 +15.4%, 2026-03 -1.2%, 2026-04 -0.0%, 2026-05 -5.0%

## AMZN

| | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |
|---|---|---|---|---|
| Cum. return | +15.5% | +13.3% | +15.3% | +24.5% |
| Sharpe | 1.67 | 1.46 | 1.31 | 2.74 |
| Sortino | 2.56 | | 2.15 | |
| Max drawdown | -13.5% | -14.5% | -19.6% | |

Ann.vol 23% · alpha(ann) +15.6% · beta 0.56 · turnover 19 · 67% days long
Decisions: 66 buy / 15 hold / 21 sell · momentum-agreement 76% (n=84) · guardrails: 0 re-asks / 0 fallbacks
Per-month (10bps): 2026-01 +6.8%, 2026-02 -2.8%, 2026-03 -8.7%, 2026-04 +27.4%, 2026-05 -6.3%

## MSFT

| | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |
|---|---|---|---|---|
| Cum. return | -3.9% | -5.5% | -2.2% | -6.0% |
| Sharpe | -0.20 | -0.35 | -0.00 | -0.56 |
| Sortino | -0.20 | | -0.00 | |
| Max drawdown | -20.8% | -21.3% | -26.0% | |

Ann.vol 28% · alpha(ann) -5.6% · beta 0.76 · turnover 17 · 72% days long
Decisions: 56 buy / 28 hold / 18 sell · momentum-agreement 74% (n=72) · guardrails: 0 re-asks / 0 fallbacks
Per-month (10bps): 2026-01 -10.6%, 2026-02 -8.8%, 2026-03 +1.7%, 2026-04 +10.3%, 2026-05 +3.3%

## COIN

| | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |
|---|---|---|---|---|
| Cum. return | -18.5% | -20.5% | -22.8% | -24.2% |
| Sharpe | -0.70 | -0.81 | -0.44 | -1.49 |
| Sortino | -1.02 | | -0.82 | |
| Max drawdown | -28.0% | -29.2% | -44.9% | |

Ann.vol 53% · alpha(ann) -21.5% · beta 0.46 · turnover 24 · 57% days long
Decisions: 52 buy / 16 hold / 34 sell · momentum-agreement 70% (n=84) · guardrails: 4 re-asks / 0 fallbacks
Per-month (10bps): 2026-01 -7.6%, 2026-02 +7.7%, 2026-03 -11.9%, 2026-04 +5.1%, 2026-05 -13.8%

## Mean across 5 tickers (0bps)

| | FinMem-Ours | Buy&Hold | No-memory |
|---|---|---|---|
| Cum. return | -5.3% | -4.1% | +1.7% |
| Sharpe | -0.15 | 0.11 | 0.38 |

## Memory effect (audited)

FinMem-Ours mean CR **-5.3%** · Buy&Hold **-4.1%** · No-memory **+1.7%** (0bps). FinMem-Ours UNDERPERFORMS Buy&Hold on the mean; the no-memory ablation is the best of the three and beats full FinMem-Ours on **3/5** tickers. The layered memory did not add value out-of-sample (direction unchanged from the pre-audit conclusion, magnitude much smaller).

**Pooled Wilcoxon** Ours vs B&H (n=200): p=0.6917, median daily edge -3.0 bps.
**Pooled Wilcoxon** Ours vs No-memory (n=172): p=0.0751, median daily memory effect -28.0 bps (neg ⇒ memory hurt).

## Exhibit: TSLA as-shipped (frozen `f170a92`) — canonical

As-shipped TSLA: CR -9.2% (0bps), Sharpe -0.50 vs FinMem-Ours TSLA CR -23.1%. Both lose to B&H (-5.1%); as-shipped was a 100%-momentum follower with a 3-day-revolving deep layer (F1/F2, DEEP_LAYER_TRACE.md).

## Portfolio layer (our extension)
_(reported as logged; recompute under the canonical convention is in the deck figures.)_ Allocator CR -3.6% vs equal-weight B&H -0.4%.

---
_Canonical numbers from 16_canonical_metrics.py · full table data/09_results/metrics_canonical.md · figures data/09_results/figures/ · see DEEP_DIVE.md + deck_excerpts.md._
