# Canonical metrics — FinMem-Ours (audited, Stage 11)

**Convention:** simple daily returns, position = carry-forward unit long-only {0,+1} (buy=enter/keep, sell=exit, hold=carry) × next-day move, compounded, on the FULL env price series incl. the terminal day. Costs = bps × turnover. This SUPERSEDES the earlier RESULTS, which used raw decisions as the position (hold=flat, sell=SHORT) + log returns and inflated every cell (see 15_reconcile.py).

| Ticker | Strategy | CR 0bps | CR 10bps | Ann.ret | Ann.vol | Sharpe | Sortino | MaxDD | alpha(ann) | beta | turn | %long |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TSLA | FinMem-Ours | -23.1% | -25.5% | -47.8% | +31.2% | -1.92 | -2.57 | -30.2% | -56.6% | 0.65 | 31 | +53.9% |
| TSLA | BuyHold | -5.1% | -5.2% | -12.1% | +39.0% | -0.14 | -0.25 | -24.0% | +0.0% | 1.00 | 1 | +100.0% |
| TSLA | No-memory | -5.5% | -8.0% | -13.0% | +27.8% | -0.37 | -0.47 | -26.2% | -7.5% | 0.51 | 27 | +43.1% |
| TSLA | LC-Trader | -7.9% | -8.1% | -18.3% | +38.7% | -0.33 | -0.61 | -24.0% | -7.6% | 0.98 | 3 | +98.1% |
| TSLA | As-shipped | -9.2% | -10.2% | -21.1% | +35.0% | -0.50 | -0.82 | -26.6% | -13.4% | 0.81 | 11 | +80.4% |
| NFLX | FinMem-Ours | +3.8% | +1.9% | +9.7% | +34.1% | 0.44 | 0.48 | -15.4% | +20.8% | 0.81 | 18 | +54.9% |
| NFLX | BuyHold | -5.6% | -5.7% | -13.4% | +37.9% | -0.19 | -0.30 | -20.7% | +0.0% | 1.00 | 1 | +100.0% |
| NFLX | No-memory | +19.8% | +17.5% | +56.4% | +31.8% | 1.56 | 1.36 | -13.3% | +54.9% | 0.71 | 20 | +39.2% |
| AMZN | FinMem-Ours | +15.5% | +13.3% | +42.7% | +22.9% | 1.67 | 2.56 | -13.5% | +15.6% | 0.56 | 19 | +66.7% |
| AMZN | BuyHold | +15.3% | +15.2% | +42.3% | +30.5% | 1.31 | 2.15 | -19.6% | +0.0% | 1.00 | 1 | +100.0% |
| AMZN | No-memory | +24.5% | +22.1% | +71.7% | +20.5% | 2.74 | 4.15 | -6.8% | +38.0% | 0.46 | 19 | +53.9% |
| MSFT | FinMem-Ours | -3.9% | -5.5% | -9.3% | +28.4% | -0.20 | -0.20 | -20.8% | -5.6% | 0.76 | 17 | +71.6% |
| MSFT | BuyHold | -2.2% | -2.3% | -5.3% | +32.7% | -0.00 | -0.00 | -26.0% | +0.0% | 1.00 | 1 | +100.0% |
| MSFT | No-memory | -6.0% | -8.2% | -14.2% | +22.8% | -0.56 | -0.37 | -16.0% | -12.6% | 0.49 | 23 | +42.2% |
| COIN | FinMem-Ours | -18.5% | -20.5% | -39.7% | +52.8% | -0.70 | -1.02 | -28.0% | -21.5% | 0.46 | 24 | +56.9% |
| COIN | BuyHold | -22.8% | -22.9% | -47.2% | +78.1% | -0.44 | -0.82 | -44.9% | +0.0% | 1.00 | 1 | +100.0% |
| COIN | No-memory | -24.2% | -25.9% | -49.5% | +40.5% | -1.49 | -1.62 | -25.1% | -51.0% | 0.27 | 23 | +37.3% |

## Means (cum return 0bps)

- FinMem-Ours **-5.3%** · No-memory **+1.7%** · Buy&Hold **-4.1%** · LC-Trader **-7.9%**
- Mean Sharpe: Ours -0.15 · No-mem 0.38 · B&H 0.11 · LC-Trader -0.33
- No-memory > FinMem-Ours on **3/5** tickers (cum return).

**Pooled Wilcoxon** Ours vs B&H (n=200): p=0.6917, median daily edge -3.0 bps.
**Pooled Wilcoxon** Ours vs No-memory (n=172): p=0.0751, median daily memory effect -28.0 bps (neg ⇒ memory hurt).
**Pooled Wilcoxon** FinMem-Ours vs LC-Trader (n=49): p=0.1978, median daily edge -49.2 bps (neg ⇒ LC-Trader better).
Bootstrap 95% CI on pooled Ours daily Sharpe: (-1.80, 1.20).
