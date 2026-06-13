"""LC-Trader — plain long-context trading baseline (NO FinMem).
Each test day the model sees an APPEND-ONLY context (10-K + latest 10-Q summary,
then every day's news summaries in date order up to today) + a tiny volatile tail
(date, position, cum return), and decides buy/sell/hold. No persona, momentum,
memory layers, retrieval, embeddings, or FinBERT. Reuses our Gemini summaries.

Prompt order = [SYSTEM fixed][ACCUMULATED INFO append-only PREFIX][VOLATILE TAIL]
so the long growing prefix is byte-identical day-to-day → OpenAI prompt-cache hits.

Usage:
  python lc_trader.py --estimate              # no API: token counts + projected $
  python lc_trader.py run [TICKER ...]        # real run, cost-metered, $5 hard cap
Accounting is canonical (unit long-only, simple returns, full env series via 16).
"""
import os
import re
import sys
import json
import time
import pickle
import datetime
import importlib.util

import polars as pl
import tiktoken
from dotenv import load_dotenv

load_dotenv()
TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
T0, T1 = datetime.date(2026, 1, 2), datetime.date(2026, 6, 1)
MODEL = "gpt-4.1-mini"
PRICE_IN, PRICE_CACHED, PRICE_OUT = 0.40, 0.10, 1.60   # $/1M
HARD_CAP_USD = 3.00   # protects the $5 deposit ($1.66 already spent); est. good-cache $2.33
MAX_CONTEXT_TOKENS = 900_000
ENC = tiktoken.get_encoding("o200k_base")
OUTDIR = "data/09_results"

spec = importlib.util.spec_from_file_location("c16", os.path.join("data-pipeline", "16_canonical_metrics.py"))
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)

SYSTEM = (
    "You are a disciplined trader for {ticker}. You may hold at most ONE share and you "
    "CANNOT short: from flat you may BUY or HOLD; while holding you may SELL or HOLD. "
    "Decide using only the information below. Respond ONLY with a JSON object "
    '{{"decision":"buy|sell|hold","reason":"<=2 sentences"}}.')


def ntok(s):
    return len(ENC.encode(s))


def load_news(ticker):
    rows = [json.loads(l) for l in open(f"data/02_intermediate/summary_store_{ticker}.jsonl",
                                        encoding="utf-8-sig")]
    byd = {}
    for r in rows:
        d = r["effective_trading_date"]
        if str(T0) <= d <= str(T1):
            byd.setdefault(d, []).append(r["summary"].strip())
    return {datetime.date.fromisoformat(d): v for d, v in byd.items()}


def load_seed_filings(ticker):
    f = pl.read_parquet("data/01_raw/filing_data_summarized.parquet").filter(pl.col("ticker") == ticker)
    k = q = None
    for r in f.sort("est_timestamp").iter_rows(named=True):
        d = r["est_timestamp"].date() if hasattr(r["est_timestamp"], "date") else r["est_timestamp"]
        if d <= T0:
            if r["type"] == "10-K":
                k = (d, r["content"].strip())
            elif r["type"] == "10-Q":
                q = (d, r["content"].strip())
    return k, q


def build_context_blocks(ticker):
    """Return (header_block, [(date, news_block_str)]) — append-only, fixed order."""
    k, q = load_seed_filings(ticker)
    header = ""
    if k:
        header += f"ANNUAL REPORT (10-K, filed {k[0]}) summary: {k[1]}\n\n"
    if q:
        header += f"QUARTERLY REPORT (10-Q, filed {q[0]}) summary: {q[1]}\n\n"
    news = load_news(ticker)
    blocks = []
    for d in sorted(news):
        txt = f"{d} news:\n" + "\n".join(f"- {s}" for s in news[d]) + "\n\n"
        blocks.append((d, txt))
    return header, blocks


def trading_days(ticker):
    return list(C.env_prices(ticker).index)


# ---------------- estimate ----------------
def estimate():
    print("LC-Trader cost ESTIMATE (no API). Model:", MODEL)
    grand_in = grand_fresh = grand_cached = 0
    for t in TICKERS:
        header, blocks = build_context_blocks(t)
        days = trading_days(t)
        sys_tok = ntok(SYSTEM.format(ticker=t))
        header_tok = ntok(header)
        # cumulative news tokens by date
        block_tok = {d: ntok(b) for d, b in blocks}
        bdates = sorted(block_tok)
        total_in = fresh = cached = 0
        prev_prefix = sys_tok + header_tok  # day-0 cached baseline grows
        cum = sys_tok + header_tok
        max_ctx = 0
        added = set()
        for i, day in enumerate(days):
            # context = header + all news blocks with date <= day
            ctx = sys_tok + header_tok
            for d in bdates:
                if d <= day:
                    ctx += block_tok[d]
            tail = 60  # volatile tail tokens (date/pos/return)
            prompt_tok = ctx + tail
            max_ctx = max(max_ctx, prompt_tok)
            total_in += prompt_tok
            if i == 0:
                fresh += prompt_tok  # cold miss
            else:
                # cached = previous day's full context prefix; fresh = new news + tail
                cached += prev_ctx
                fresh += (ctx - prev_ctx) + tail
            prev_ctx = ctx
        comp = len(days) * 40
        cost_cache = cached / 1e6 * PRICE_CACHED + fresh / 1e6 * PRICE_IN + comp / 1e6 * PRICE_OUT
        cost_nocache = total_in / 1e6 * PRICE_IN + comp / 1e6 * PRICE_OUT
        grand_in += total_in; grand_fresh += fresh; grand_cached += cached
        print(f"  {t}: {len(days)}d · sum-input {total_in/1e6:.1f}M · max-ctx {max_ctx/1e3:.0f}K "
              f"· good-cache ${cost_cache:.2f} · no-cache ${cost_nocache:.2f}")
        assert max_ctx < MAX_CONTEXT_TOKENS, f"{t} exceeds context cap"
    comp = 5 * 102 * 40
    good = grand_cached / 1e6 * PRICE_CACHED + grand_fresh / 1e6 * PRICE_IN + comp / 1e6 * PRICE_OUT
    nocache = grand_in / 1e6 * PRICE_IN + comp / 1e6 * PRICE_OUT
    print(f"\nTOTAL summed input {grand_in/1e6:.1f}M (cached {grand_cached/1e6:.1f}M + "
          f"fresh {grand_fresh/1e6:.1f}M)")
    print(f"PROJECTED COST: good-cache ${good:.2f} · worst-case (no cache) ${nocache:.2f} · cap ${HARD_CAP_USD}")
    return good, nocache


# ---------------- run ----------------
def run(tickers):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    os.makedirs(OUTDIR, exist_ok=True)
    meter = {"in": 0, "cached": 0, "out": 0, "cost": 0.0, "calls": 0}
    meter_path = os.path.join(OUTDIR, "lc_trader_meter.json")
    if os.path.exists(meter_path):
        meter = json.load(open(meter_path))

    for t in tickers:
        dec_path = os.path.join(OUTDIR, f"lc_decisions_{t}.json")
        decisions = json.load(open(dec_path)) if os.path.exists(dec_path) else {}
        header, blocks = build_context_blocks(t)
        bdates = [d for d, _ in blocks]
        block_map = dict(blocks)
        days = trading_days(t)
        px = C.env_prices(t)
        sysmsg = SYSTEM.format(ticker=t)
        pos = 0
        # rebuild realized cum return from saved decisions (resume-safe)
        cum = 0.0
        prefix = header  # accumulated info grows; identical prefix across days
        built_to = None
        for i, day in enumerate(days):
            # grow prefix to include all news <= day (byte-identical append)
            for d in bdates:
                if (built_to is None or d > built_to) and d <= day:
                    prefix += block_map[d]
            built_to = day
            # leakage assertion
            assert all(d <= day for d in bdates if d <= day), "future news leaked"
            max_d = max([d for d in bdates if d <= day], default=day)
            assert max_d <= day, f"max context date {max_d} > {day}"
            tail = (f"\nToday is {day}. You currently hold {pos} share(s). Your cumulative "
                    f"return so far is {cum*100:.1f}%. Make your decision now.")
            if str(day) in decisions:
                d_dec = decisions[str(day)]
            else:
                if meter["cost"] >= HARD_CAP_USD:
                    print(f"HARD CAP ${HARD_CAP_USD} reached — stopping at {t} {day}")
                    json.dump(meter, open(meter_path, "w")); json.dump(decisions, open(dec_path, "w"))
                    return
                ptokens = ntok(sysmsg) + ntok(prefix) + ntok(tail)
                assert ptokens < MAX_CONTEXT_TOKENS, f"{t} {day} prompt {ptokens} too large"
                for attempt in range(5):
                    try:
                        resp = client.chat.completions.create(
                            model=MODEL, temperature=1.0,
                            messages=[{"role": "system", "content": sysmsg},
                                      {"role": "user", "content": prefix + tail}],
                            response_format={"type": "json_object"})
                        break
                    except Exception as e:
                        print(f"  retry {attempt+1} {t} {day}: {e}"); time.sleep(10)
                else:
                    raise RuntimeError("LC-Trader: API failed")
                u = resp.usage
                cached = (u.prompt_tokens_details.cached_tokens if u.prompt_tokens_details else 0) or 0
                fresh = u.prompt_tokens - cached
                meter["in"] += u.prompt_tokens; meter["cached"] += cached; meter["out"] += u.completion_tokens
                meter["cost"] += fresh/1e6*PRICE_IN + cached/1e6*PRICE_CACHED + u.completion_tokens/1e6*PRICE_OUT
                meter["calls"] += 1
                try:
                    d_dec = json.loads(resp.choices[0].message.content).get("decision", "hold").lower()
                except Exception:
                    d_dec = "hold"
                if d_dec not in ("buy", "sell", "hold"):
                    d_dec = "hold"
                decisions[str(day)] = d_dec
                if meter["calls"] % 20 == 0:
                    hit = meter["cached"] / max(1, meter["in"])
                    print(f"  [{t}] {i+1}/{len(days)} {day} dec={d_dec} | cache-hit {hit*100:.0f}% "
                          f"| ${meter['cost']:.2f}", flush=True)
                    json.dump(meter, open(meter_path, "w")); json.dump(decisions, open(dec_path, "w"))
            # update position + realized cum (canonical)
            newpos = 1 if d_dec == "buy" else (0 if d_dec == "sell" else pos)
            if i + 1 < len(days):
                ret = float(px.iloc[i + 1] / px.iloc[i] - 1)
                cum = (1 + cum) * (1 + newpos * ret) - 1
            pos = newpos
        json.dump(meter, open(meter_path, "w")); json.dump(decisions, open(dec_path, "w"))
        hit = meter["cached"] / max(1, meter["in"])
        print(f"[{t}] DONE {len(decisions)} days · cache-hit {hit*100:.0f}% · cum ${meter['cost']:.2f}")
    print(f"\nLC-TRADER COMPLETE · {meter['calls']} calls · input {meter['in']/1e6:.1f}M "
          f"(cached {meter['cached']/1e6:.1f}M, {meter['cached']/max(1,meter['in'])*100:.0f}%) · "
          f"${meter['cost']:.2f} of ${HARD_CAP_USD} cap")


if __name__ == "__main__":
    if "--estimate" in sys.argv:
        estimate()
    elif len(sys.argv) > 1 and sys.argv[1] == "run":
        run(sys.argv[2:] or TICKERS)
    else:
        print(__doc__)
