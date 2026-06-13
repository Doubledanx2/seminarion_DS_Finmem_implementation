# RESULTS — FinMem-Ours (frozen #3, `96d724d`) · test 2026-01-02 → 2026-06-01

Paper architecture + all our fixes. Train 2025-07-01→12-31. Pre-declared comparisons: FinMem-Ours vs Buy&Hold, vs no-memory ablation, vs TSLA as-shipped (exhibit). Long-only unit positions; metrics on direction×next-day log return.


## TSLA

| | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |
|---|---|---|---|---|
| Cum. return | -25.8% | -30.5% | -0.5% | -11.1% |
| Sharpe | -2.04 | -2.50 | -0.03 | -0.79 |
| Max drawdown | -33.0% | -36.4% | -24.0% | |

Break-even vs B&H: **0.0 bps** · Wilcoxon (Ours vs B&H daily) p=0.274 (n=53) · bootstrap Sharpe 95% CI (-5.75, 0.89)
Decisions: 49 buy / 11 hold / 42 sell · momentum-agreement 73% (n=89) · guardrails: 6 re-asks / 0 fallbacks · top-5-day share -0.60
Per-month (10bps): 2026-01 -13.8%, 2026-02 -5.2%, 2026-03 -13.3%, 2026-04 -1.2%, 2026-05 -0.6%

## NFLX

| | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |
|---|---|---|---|---|
| Cum. return | +19.1% | +14.1% | -5.5% | +57.0% |
| Sharpe | 1.22 | 0.92 | -0.37 | 3.12 |
| Max drawdown | -10.9% | -12.0% | -20.7% | |

Break-even vs B&H: **53.7 bps** · Wilcoxon (Ours vs B&H daily) p=0.324 (n=53) · bootstrap Sharpe 95% CI (-2.20, 3.90)
Decisions: 48 buy / 28 hold / 26 sell · momentum-agreement 77% (n=71) · guardrails: 0 re-asks / 0 fallbacks · top-5-day share 2.18
Per-month (10bps): 2026-01 -4.0%, 2026-02 +15.5%, 2026-03 -1.6%, 2026-04 +4.6%, 2026-05 +0.0%

## AMZN

| | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |
|---|---|---|---|---|
| Cum. return | +23.8% | +18.8% | +19.5% | +46.8% |
| Sharpe | 1.88 | 1.50 | 1.48 | 3.48 |
| Max drawdown | -18.0% | -19.4% | -19.6% | |

Break-even vs B&H: **8.6 bps** · Wilcoxon (Ours vs B&H daily) p=0.883 (n=36) · bootstrap Sharpe 95% CI (-2.89, 5.35)
Decisions: 66 buy / 15 hold / 21 sell · momentum-agreement 76% (n=84) · guardrails: 0 re-asks / 0 fallbacks · top-5-day share 1.33
Per-month (10bps): 2026-01 +7.4%, 2026-02 +11.1%, 2026-03 -17.8%, 2026-04 +27.4%, 2026-05 -4.9%

## MSFT

| | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |
|---|---|---|---|---|
| Cum. return | -7.0% | -10.8% | -4.4% | -7.7% |
| Sharpe | -0.62 | -0.98 | -0.34 | -0.65 |
| Max drawdown | -19.1% | -20.5% | -26.0% | |

Break-even vs B&H: **0.0 bps** · Wilcoxon (Ours vs B&H daily) p=0.762 (n=46) · bootstrap Sharpe 95% CI (-4.51, 2.99)
Decisions: 56 buy / 28 hold / 18 sell · momentum-agreement 74% (n=72) · guardrails: 0 re-asks / 0 fallbacks · top-5-day share -1.65
Per-month (10bps): 2026-01 -10.4%, 2026-02 -9.0%, 2026-03 +7.5%, 2026-04 +8.3%, 2026-05 -6.0%

## COIN

| | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |
|---|---|---|---|---|
| Cum. return | -22.0% | -26.3% | -20.1% | -23.8% |
| Sharpe | -0.98 | -1.21 | -0.72 | -0.93 |
| Max drawdown | -46.0% | -48.0% | -44.9% | |

Break-even vs B&H: **0.0 bps** · Wilcoxon (Ours vs B&H daily) p=0.836 (n=49) · bootstrap Sharpe 95% CI (-4.01, 2.15)
Decisions: 52 buy / 16 hold / 34 sell · momentum-agreement 70% (n=84) · guardrails: 4 re-asks / 0 fallbacks · top-5-day share -1.60
Per-month (10bps): 2026-01 +10.9%, 2026-02 +13.4%, 2026-03 -16.8%, 2026-04 -0.1%, 2026-05 -29.5%

## Mean across completed tickers

| metric | FinMem-Ours 0bps | FinMem-Ours 10bps | Buy&Hold | No-memory 0bps |
|---|---|---|---|---|
| Cum. return | -2.4% | -6.9% | -2.2% | +12.3% |
| Sharpe | -0.11 | -0.45 | 0.00 | 0.84 |
| Mean break-even 12 bps · mean momentum-agreement 74% · total guardrail re-asks 10, fallbacks 0 |

### Memory effect (headline)

No-memory ablation mean CR **+12.3%** vs FinMem-Ours **-2.4%** vs B&H -2.2% (0bps). Removing memory HELPED on 3/5 tickers — the layered-memory module did not add value on leakage-free out-of-sample data (and hurt on average). This is the central negative result.

**Pooled Wilcoxon** (all tickers, FinMem-Ours vs B&H daily, n=237): p=0.7936; median daily edge +4.5 bps.
**Pooled Wilcoxon** (FinMem-Ours vs no-memory daily, n=250): p=0.1301; median daily memory effect -14.0 bps (negative ⇒ memory hurt).

## Exhibit: TSLA as-shipped (frozen `f170a92`) — before/after our fixes

As-shipped TSLA test: CR -1.9% (0bps), Sharpe -0.16, break-even 0.0 bps, 100% momentum agreement (pure momentum follower; deep memory was a 3-day revolving door — see DEEP_LAYER_TRACE.md). FinMem-Ours TSLA row above is the after.

## Portfolio layer (our extension)

Allocator portfolio CR -3.6% vs equal-weight B&H -0.4% over 102 test days.

---
_Generated from checkpoints by 12_final_report.py · 5/5 tickers complete · see DEEP_DIVE.md for decision/memory analysis._
