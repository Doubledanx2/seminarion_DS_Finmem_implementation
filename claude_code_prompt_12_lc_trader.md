# Prompt for Claude Code — Stage 12: LC-Trader baseline (NO FinMem, cached long context)

Copy below into Claude Code. This is a NEW baseline Dan wants: a plain long-context
trader with zero FinMem architecture, to isolate "does FinMem beat just giving a modern
long-context model the news?". It is NOT the existing no-memory ablation (that still ran
inside FinMem's persona/momentum/retrieval scaffolding). Build it clean and cache-cheap.

---

## What LC-Trader is (and is NOT)

- NO persona, NO risk-inclination lines, NO momentum sentence, NO FinMem prompt
  templates, NO memory layers, NO retrieval, NO FAISS, NO embeddings, NO FinBERT scores.
- Just: each test day, the model sees an APPEND-ONLY context — the 10-K summary + latest
  10-Q summary (seeded at day 1) followed by every day's news summaries in date order up
  to and including today — plus its current position and cumulative return, and decides
  buy / sell / hold. No shorting.
- Reuse OUR existing Gemini news+filing summaries (data/02_intermediate/summary_store_*).
  Do NOT re-summarize. Strip the FinBERT sentiment line (LC-Trader sees plain news).

## Daily prompt structure (ORDER IS CRITICAL FOR CACHING)

Build the prompt so the long, growing, identical part is the PREFIX and the small
volatile part is the SUFFIX — this maximizes OpenAI prompt-cache hits.

```
[SYSTEM / fixed instructions]            <- identical every day (cache)
You are a disciplined trader for {TICKER}. You may hold at most ONE share and you
CANNOT short: from flat you may BUY or HOLD; while holding you may SELL or HOLD.
Decide using only the information below. Respond ONLY with
{"decision":"buy|sell|hold","reason":"<=2 sentences"}.

[ACCUMULATED INFORMATION — append-only, oldest first]   <- grows daily, prefix (cache)
ANNUAL REPORT (10-K) summary: ...
QUARTERLY REPORT (10-Q) summary: ...
2026-01-02 news: <summaries>
2026-01-05 news: <summaries>
... (every prior day, in fixed order, never reordered/edited)
2026-06-01 news: <today's summaries>          <- only NEW text vs yesterday

[VOLATILE TAIL — changes daily, kept LAST]              <- tiny, fresh each day
Today is {DATE}. You currently hold {0 or 1} share(s). Your cumulative return so far
is {X.X}%. Make your decision now.
```

Rules: the prefix must be byte-identical to the previous day's prefix (same news, same
order, no reformatting) so the cache matches from token 0. Put the date/position/return
ONLY in the volatile tail.

## Caching & cost controls

- Use the OpenAI prompt cache (automatic >1024 tokens). Run each ticker's 102 days in
  ONE tight sequential loop so the cache stays warm (TTL ~5-10 min). Day 1 is a cold miss.
- Log per-call `prompt_tokens`, `cached_tokens` (from usage.prompt_tokens_details),
  `completion_tokens`; sum a real $ cost using $0.40/M input, $0.10/M cached, $1.60/M out.
- Expected ~30.6M input total; with good cache hits ~$3.5. HARD CAP $5.00 (extend the
  TokenMeter abort); if Dan's balance is low, fall back to the free pool across days.
- Final-day context maxes ~182K tokens (TSLA) — within gpt-4.1-mini's 1M window. If any
  prompt would exceed ~900K tokens, stop and report (won't happen here, but assert it).

## Accounting & integrity (identical to canonical so it's comparable)

- Unit long-only {0,+1}; buy=enter/keep, sell=exit-only-if-holding, hold=carry.
- Price decisions on the FULL env series incl. the terminal day (the canonical
  convention from Stage 11; reuse 16_canonical_metrics.py). 0 and 10 bps.
- Leakage: only summaries dated <= the simulated day enter the context (they already
  carry our verified dates). Add an assertion: max(context date) <= cur_date each day.
- Run all 5 tickers (TSLA NFLX AMZN MSFT COIN), test window 2026-01-02 -> 2026-06-01.

## Deliverables

1. `lc_trader.py` (standalone; no puppy imports needed beyond data loading).
2. Per-ticker results folded into `metrics_canonical.{md,csv}` as a 4th strategy column:
   FinMem-Ours / No-memory / **LC-Trader** / Buy&Hold (CR, Sharpe, MDD, turnover ± costs;
   pooled + per-ticker Wilcoxon LC-Trader vs B&H and vs FinMem-Ours).
3. `equity_<TKR>.png` regenerated to include the LC-Trader line; one `bars_cum_return`
   refresh with the 4th series.
4. A short `LC_TRADER.md`: design, the exact daily prompt template, total tokens,
   cached-token %, real $ spent, and the verdict vs FinMem-Ours and vs B&H.
5. STATUS truthful; log cached-token hit rate (it's a headline efficiency stat).

## Framing for the report
LC-Trader answers the cleanest version of our question: in a 1M-token-context world,
does FinMem's whole memory+persona apparatus beat simply streaming the same news into a
plain long-context model? Whatever the result, it's the strongest baseline in the deck.
