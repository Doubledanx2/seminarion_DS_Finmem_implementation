# LC-Trader — plain long-context baseline (no FinMem)

**Question it answers:** in a 1M-token-context world, does FinMem's whole memory + persona + retrieval apparatus beat simply streaming the same news into a plain long-context model? LC-Trader has **none** of FinMem's scaffolding — no persona, no risk/momentum lines, no memory layers, no retrieval/FAISS/embeddings, no FinBERT. It reuses our Gemini news+filing summaries (sentiment line stripped).

## Design

- Each test day: SYSTEM (fixed) + APPEND-ONLY context (10-K + latest 10-Q summary, then every day's news summaries in date order ≤ today) + a tiny volatile tail (date, position, cumulative return). Prefix is byte-identical day-to-day → OpenAI prompt-cache hits from token 0.

- Accounting identical to canonical: unit long-only {0,+1}, simple returns, full env series incl. terminal day, 0 & 10 bps. Leakage assert: max(context date) ≤ cur_date.

## Exact daily prompt template
```
[SYSTEM] You are a disciplined trader for TSLA. You may hold at most ONE share and you CANNOT short: from flat you may BUY or HOLD; while holding you may SELL or HOLD. Decide using only the information below. Respond ONLY with a JSON object {"decision":"buy|sell|hold","reason":"<=2 sentences"}.

[ACCUMULATED INFO — append-only, oldest first]
ANNUAL REPORT (10-K, filed 2025-01-29) summary: <...>
QUARTERLY REPORT (10-Q, filed 2025-10-22) summary: <...>
2026-01-02 news:
- <summary>
- <summary>
2026-01-05 news:
- <summary>
... (every prior day, fixed order, never edited)
[VOLATILE TAIL]
Today is 2026-03-16. You currently hold 1 share(s). Your cumulative return so far is -4.2%. Make your decision now.
```

## Efficiency (the headline caching stat)

- Calls: 103 · input tokens 7.0M · **cached 6.8M (97% cache-hit)** · output 5K
- **Real cost: $0.78** (vs $2.82 with no caching) — the 97% prefix-cache hit cut spend ~72%.

## Results (canonical, 0bps cum return)

| Ticker | LC-Trader | FinMem-Ours | Buy&Hold |
|---|---|---|---|
| TSLA | -7.9% | -23.1% | -5.1% |
| NFLX | — | +3.8% | -5.6% |
| AMZN | — | +15.5% | +15.3% |
| MSFT | — | -3.9% | -2.2% |
| COIN | — | -18.5% | -22.8% |

_LC-Trader was run on **TSLA only** (stopped after TSLA per request); the other tickers show '—'._

**Verdict (TSLA):** LC-Trader CR **-7.9%** (Sharpe -0.33, 98% days long, turnover 3) **beats FinMem-Ours** (-23.1%), vs Buy&Hold -5.1%, No-memory -5.5%. The plain long-context model was almost entirely passive (held ~all days) and tracked the market, while FinMem's apparatus actively traded itself well below it. Pooled Wilcoxon LC vs Ours / LC vs B&H in metrics_canonical.md.

## Cost-scaling note
Cumulative cost grows ~**quadratically** with horizon length: the append-only context expands linearly (toward ~135K tokens by day 103), and even at 97% cache-hit the $0.10/M cached rate is charged on the whole growing prefix every day. The last ~40 days also hit OpenAI's 200K TPM limit (auto-retried). FinMem's fixed-size memory has no such horizon-scaling cost — a structural trade-off worth a slide.
