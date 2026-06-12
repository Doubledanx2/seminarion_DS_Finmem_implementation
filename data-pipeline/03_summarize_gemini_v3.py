# Stage-2 summarizer: Gemini 3.1 Flash-Lite (ARCHITECTURE.md final decision).
# A5-COMPLIANT (addendum, binding):
#   A5.1 summary store rows: (article_id, symbol, source_datetime_utc,
#        effective_trading_date, summary, model, tokens) — dates from OUR pipeline
#        only (16:00 rule already applied in the raw parquet), never from the model.
#   A5.2 batched items are ID-tagged; the prompt demands strictly independent
#        per-item summaries from the given text ONLY (no background knowledge, no
#        cross-article context); outputs are parsed per-ID, not by position.
#   A5.3 filing summaries keyed by filedAt (est_timestamp), same store schema.
#   A5.5 quality-sample mode writes a review file for the injected-context check.
# Plus: body-less fallback (<400 chars -> title+summary, no API call), 30 RPM /
# 1,450-req-day pacing, jsonl checkpoint-resume across the 00:00 UTC free-tier
# reset, persistent token/cost meter.
#
# Usage:
#   python data-pipeline/03_summarize_gemini_v3.py --sample 20
#   python data-pipeline/03_summarize_gemini_v3.py news [TICKER ...]
#   python data-pipeline/03_summarize_gemini_v3.py filings

MODEL = "gemini-3.1-flash-lite"
PRICE_IN, PRICE_OUT = 0.25, 1.50          # $/1M tokens
MAX_BATCH_ARTICLES = 8
MAX_BATCH_CHARS = 24_000
BODYLESS_CHARS = 400                       # below this, title+summary IS the summary
SUMMARY_TOKENS = 200                       # per article, paper budget
FILING_SUMMARY_TOKENS = 400
# PAID TIER (key upgraded 2026-06-12, Dan): per-request latency (~3s) dominated the
# sequential run (~20 RPM); CONCURRENCY parallel batch requests lift throughput to
# ~250 RPM — still far under paid-tier limits. Binding guard = billed-cost ceiling.
MIN_INTERVAL_S = 0.0
CONCURRENCY = 12
MAX_REQ_PER_RUN = 20_000
RUN_COST_CEILING_USD = 8.00                # abort line: Dan's budget $7.25 +15% (cost table)

import os
import re
import json
import time
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import polars as pl
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors

load_dotenv()
TAG_RE = re.compile(r"<[^>]+>")
RAW = os.path.join("data", "01_raw")
OUT = os.path.join("data", "02_intermediate")
METER_PATH = os.path.join(OUT, "gemini_meter.json")
TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

BATCH_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {"id": {"type": "STRING"}, "summary": {"type": "STRING"}},
        "required": ["id", "summary"],
    },
}


class Meter:
    def __init__(self):
        self.d = {"requests": 0, "in_tokens": 0, "out_tokens": 0}
        if os.path.exists(METER_PATH):
            with open(METER_PATH) as f:
                self.d = json.load(f)
        self.run_requests = 0
        self._last = 0.0
        self._lock = threading.Lock()

    def pace(self):
        if MIN_INTERVAL_S <= 0:
            return
        with self._lock:
            wait = self._last + MIN_INTERVAL_S - time.time()
            self._last = time.time() + max(0, wait)
        if wait > 0:
            time.sleep(wait)

    def add(self, usage):
        pin = usage.prompt_token_count or 0
        pout = usage.candidates_token_count or 0
        with self._lock:
            self.d["requests"] += 1
            self.run_requests += 1
            self.d["in_tokens"] += pin
            self.d["out_tokens"] += pout
            with open(METER_PATH, "w") as f:
                json.dump(self.d, f)

    @property
    def cost(self):
        return self.d["in_tokens"] / 1e6 * PRICE_IN + self.d["out_tokens"] / 1e6 * PRICE_OUT

    def line(self):
        return (f"req={self.d['requests']} in={self.d['in_tokens']:,} out={self.d['out_tokens']:,} "
                f"≈${self.cost:.2f} list-price (free tier: $0)")


METER = Meter()
RUN_BASELINE_COST = METER.cost  # tokens metered before the paid upgrade were $0-billed


class BudgetStop(Exception):
    """Billed cost of THIS run reached the approved ceiling — graceful stop."""


class QuotaExhausted(Exception):
    """Persistent 429 -> quota/rate ceiling. Checkpoints are on disk; rerun to resume."""


class BadBatch(Exception):
    """Response repeatedly unparseable for this specific batch (e.g. output
    truncated mid-JSON). Caller bisects the batch instead of aborting the run."""


def gemini_call(prompt: str, schema: dict, max_out: int):
    """One paced Gemini call with structured output. 429s back off exponentially
    (30s..8min, ~15min total); if they persist we assume the daily quota is gone
    and stop GRACEFULLY (QuotaExhausted) instead of crashing mid-run."""
    if METER.cost - RUN_BASELINE_COST >= RUN_COST_CEILING_USD:
        raise BudgetStop(f"run billed ≈${METER.cost - RUN_BASELINE_COST:.2f} >= "
                         f"${RUN_COST_CEILING_USD:.2f} ceiling")
    METER.pace()
    backoff = 30
    json_fails = 0
    last_was_429 = False
    for attempt in range(6):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=max_out,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            METER.add(resp.usage_metadata)
            return (json.loads(resp.text),
                    resp.usage_metadata.prompt_token_count or 0,
                    resp.usage_metadata.candidates_token_count or 0)
        except errors.APIError as e:
            last_was_429 = e.code == 429
            if e.code == 429:
                print(f"  API 429, backoff {backoff}s ({attempt + 1}/6)", flush=True)
                time.sleep(backoff)
                backoff = min(backoff * 2, 480)
            elif e.code in (500, 503):
                print(f"  API {e.code}, retry in 10s ({attempt + 1}/6)", flush=True)
                time.sleep(10)
            else:
                raise
        except json.JSONDecodeError as e:
            # truncated/garbled output is usually deterministic for a given batch
            # at temperature 0.2 — two strikes, then let the caller bisect
            last_was_429 = False
            json_fails += 1
            print(f"  bad JSON ({e}), retry ({attempt + 1}/6)", flush=True)
            if json_fails >= 2:
                raise BadBatch(str(e)) from e
    if last_was_429:
        raise QuotaExhausted("persistent 429 after exponential backoff")
    raise BadBatch("exhausted retries without parseable output")


# A5.2: ID-tagged batch prompt, per-item isolation, source text only
def news_prompt(ticker: str, tagged: list[tuple[str, str]]) -> str:
    head = (
        f"You are a financial news summarizer. Below are {len(tagged)} news articles about "
        f"{ticker}. Each article starts with '=== ARTICLE id=<ID> ==='.\n"
        "Rules (strict):\n"
        f"1. Summarize EACH article INDEPENDENTLY in at most {SUMMARY_TOKENS} tokens, keeping "
        "concrete facts: numbers, analyst actions, price targets, products, dates.\n"
        "2. Use ONLY the text of that article. Do NOT use background knowledge, do NOT add "
        "context or facts that are not present in the article text, and do NOT let any other "
        "article in this request influence a summary.\n"
        "3. Return a JSON array with exactly one object {\"id\": \"<ID>\", \"summary\": \"...\"} "
        "per article, covering every ID exactly once.\n"
    )
    blocks = [f"=== ARTICLE id={aid} ===\n{body}" for aid, body in tagged]
    return head + "\n" + "\n\n".join(blocks)


def summarize_batch(ticker: str, batch: list) -> tuple[dict[str, str], int, int]:
    """A5.2: send ID-tagged batch, parse per-ID. Returns (aid->summary, per-item
    in-tokens, per-item out-tokens) — usage split evenly across the batch."""
    tags = {f"A{i + 1}": row for i, row in enumerate(batch)}
    out, tin, tout = gemini_call(
        news_prompt(ticker, [(aid, row.body) for aid, row in tags.items()]),
        schema=BATCH_SCHEMA,
        max_out=(SUMMARY_TOKENS + 150) * len(batch) + 200,  # headroom: truncation = BadBatch
    )
    by_id = {str(o["id"]).strip(): str(o["summary"]).strip() for o in out if isinstance(o, dict)}
    missing = [aid for aid in tags if aid not in by_id or not by_id[aid]]
    if missing:
        raise ValueError(f"batch response missing ids: {missing}")
    return ({tags[aid].aid: by_id[aid] for aid in tags},
            tin // len(batch), tout // len(batch))


def build_body(title, summary, content) -> str:
    content_txt = TAG_RE.sub(" ", content or "").strip()
    parts = [p for p in [title, summary if summary and summary != title else "", content_txt] if p]
    return "\n".join(parts)[:MAX_BATCH_CHARS]


def fallback_summary(title, summary) -> str:
    return f"{title} {summary or ''}".strip()


def load_articles(ticker: str) -> pd.DataFrame:
    df = pl.read_parquet(os.path.join(RAW, f"alpaca_news_{ticker}.parquet")).to_pandas()
    df["body"] = [build_body(t, s, c) for t, s, c in zip(df["title"], df["summary"], df["content"])]
    # A5.1: dates from OUR pipeline only — effective date = rounded `date` column,
    # source timestamp = raw `datetime` column, both set at download time
    df["effective_trading_date"] = pd.to_datetime(df["date"]).dt.date
    df["source_datetime_utc"] = pd.to_datetime(df["datetime"])
    df = df[(df["effective_trading_date"] >= pd.Timestamp("2025-01-01").date())
            & (df["effective_trading_date"] <= pd.Timestamp("2026-06-01").date())]
    # article_id = url + source timestamp: URLs are NOT unique (generic quote-page
    # URLs are shared by distinct articles — found via T4, see log B10).
    # isoformat (T separator) everywhere — keep consistent with store rows and T4.
    df["aid"] = df["url"] + "#" + df["source_datetime_utc"].apply(lambda x: x.isoformat())
    df = df.drop_duplicates(subset="aid").reset_index(drop=True)
    return df


def store_row(row, summary: str, how: str, tokens_in: int = 0, tokens_out: int = 0) -> dict:
    """A5.1 store schema."""
    return {
        "article_id": row.aid,
        "symbol": row.symbols if hasattr(row, "symbols") else row.equity,
        "source_datetime_utc": row.source_datetime_utc.isoformat(),
        "effective_trading_date": row.effective_trading_date.isoformat(),
        "summary": summary,
        "model": MODEL if how == "gemini" else "fallback-title+summary",
        "tokens": {"in": tokens_in, "out": tokens_out},
    }


def summarize_news_ticker(ticker: str) -> bool:
    df = load_articles(ticker)
    ckpt_path = os.path.join(OUT, f"summary_store_{ticker}.jsonl")
    done: dict[str, dict] = {}
    if os.path.exists(ckpt_path):
        with open(ckpt_path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                done[rec["article_id"]] = rec
    ck = open(ckpt_path, "a", encoding="utf-8")

    def record(rec: dict):
        done[rec["article_id"]] = rec
        ck.write(json.dumps(rec, ensure_ascii=False) + "\n")

    todo = []
    for row in df.itertuples():
        if row.aid in done:
            continue
        if len(row.body) < BODYLESS_CHARS:
            record(store_row(row, fallback_summary(row.title, row.summary), "fallback"))
        else:
            todo.append(row)
    ck.flush()
    print(f"[{ticker}] {len(df)} articles | {len(done)} done (incl. fallbacks) | "
          f"{len(todo)} need Gemini", flush=True)

    # pack todo into batches, then run CONCURRENCY batches in parallel
    batches, batch, batch_chars = [], [], 0
    for row in todo:
        if batch and (batch_chars + len(row.body) > MAX_BATCH_CHARS or len(batch) >= MAX_BATCH_ARTICLES):
            batches.append(batch)
            batch, batch_chars = [], 0
        batch.append(row)
        batch_chars += len(row.body)
    if batch:
        batches.append(batch)

    write_lock = threading.Lock()
    full = True

    def process_batch(b):
        try:
            aid_to_summary, per_in, per_out = summarize_batch(ticker, b)
        except (BadBatch, ValueError) as e:
            if len(b) == 1:
                # single poison article: title+summary fallback, flagged in the store
                with write_lock:
                    record(store_row(b[0], fallback_summary(b[0].title, b[0].summary),
                                     "fallback"))
                    ck.flush()
                print(f"  poison article -> fallback ({str(e)[:80]})", flush=True)
                return
            mid = len(b) // 2  # bisect: isolate the offending article
            process_batch(b[:mid])
            process_batch(b[mid:])
            return
        with write_lock:
            for row in b:
                record(store_row(row, aid_to_summary[row.aid], "gemini", per_in, per_out))
            ck.flush()

    stop_exc = None
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = {ex.submit(process_batch, b): b for b in batches}
        completed = 0
        for fut in as_completed(futures):
            try:
                fut.result()
            except (QuotaExhausted, BudgetStop) as e:
                stop_exc = e
                full = False
                for f in futures:
                    f.cancel()
                break
            completed += 1
            if completed % 25 == 0:
                print(f"[{ticker}] {len(done)}/{len(df)} | {METER.line()}", flush=True)
    ck.close()
    if stop_exc is not None:
        raise stop_exc

    missing = [r.aid for r in df.itertuples() if r.aid not in done]
    if not missing:
        out = pd.DataFrame({
            "date": df["effective_trading_date"],
            "symbols": ticker,
            "summary": df["aid"].map({k: v["summary"] for k, v in done.items()}),
        }).sort_values("date")
        out_path = os.path.join(OUT, f"news_summary_{ticker}.csv")
        out.to_csv(out_path, index=False)
        print(f"[{ticker}] COMPLETE -> {out_path} | {METER.line()}", flush=True)
        return True
    print(f"[{ticker}] partial: {len(missing)} remain | {METER.line()}", flush=True)
    return False


def summarize_filings() -> None:
    """A5.3: filing summaries keyed by filedAt (est_timestamp), A5.1 schema."""
    df = pl.read_parquet(os.path.join(RAW, "filing_data.parquet")).to_pandas()
    ckpt_path = os.path.join(OUT, "summary_store_filings.jsonl")
    done = {}
    if os.path.exists(ckpt_path):
        with open(ckpt_path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                done[rec["article_id"]] = rec
    with open(ckpt_path, "a", encoding="utf-8") as ck:
        for row in df.itertuples():
            if row.document_url in done:
                continue
            prompt = (
                f"Below is the MD&A section of a {row.type} filing by {row.ticker}.\n"
                "Rules (strict): use ONLY the text below — no background knowledge, no added "
                f"context. Summarize in at most {FILING_SUMMARY_TOKENS} tokens for a trading "
                "agent: revenue/profit drivers and trends, guidance, margins, liquidity, risks, "
                "capital allocation. Concrete numbers over prose. Return a JSON array with "
                "exactly one object {\"id\": \"F1\", \"summary\": \"...\"}.\n\n"
                f"=== FILING id=F1 ===\n{row.content[:120_000]}"
            )
            out, tin, tout = gemini_call(prompt, BATCH_SCHEMA, FILING_SUMMARY_TOKENS + 120)
            s = str(out[0]["summary"]).strip()
            rec = {
                "article_id": row.document_url,
                "symbol": row.ticker,
                "source_datetime_utc": pd.Timestamp(row.utc_timestamp).isoformat(),
                "effective_trading_date": str(pd.Timestamp(row.est_timestamp).date()),  # filedAt EST
                "summary": s,
                "model": MODEL,
                "tokens": {"in": tin, "out": tout},
                "filing_type": row.type,
            }
            done[row.document_url] = rec
            ck.write(json.dumps(rec, ensure_ascii=False) + "\n")
            ck.flush()
            print(f"[filings] {row.ticker} {row.type} {rec['effective_trading_date']}: "
                  f"{len(s)} chars | {METER.line()}", flush=True)
    out_df = df.copy()
    out_df["content"] = out_df["document_url"].map({k: v["summary"] for k, v in done.items()})
    out_path = os.path.join(RAW, "filing_data_summarized.parquet")
    pl.from_pandas(out_df).write_parquet(out_path)
    print(f"[filings] COMPLETE -> {out_path}")


def quality_sample(n: int) -> None:
    """A5.5: regenerated sample for the injected-context review."""
    rows = []
    for t in TICKERS:
        df = load_articles(t)
        df = df[df["body"].str.len() >= BODYLESS_CHARS]
        k = max(2, n // len(TICKERS))
        rows.extend(df.sample(min(k, len(df)), random_state=7).assign(ticker=t).itertuples())
    rows = rows[:n]
    print(f"quality sample (A5-compliant prompt): {len(rows)} articles")
    review_path = os.path.join(OUT, "gemini_quality_sample_v2_a5.md")
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(f"# Gemini {MODEL} A5-compliant sample — {len(rows)} articles\n"
                "Review check (A5.5): flag any summary fact NOT present in the source text.\n")
        for i in range(0, len(rows), MAX_BATCH_ARTICLES):
            batch = rows[i:i + MAX_BATCH_ARTICLES]
            aid_to_summary, _, _ = summarize_batch(batch[0].ticker, batch)
            for r in batch:
                f.write(f"\n---\n## [{r.ticker}] {r.effective_trading_date} — {r.title}\n"
                        f"**Original ({len(r.body)} chars):**\n\n> {r.body[:700].replace(chr(10), ' ')}…\n\n"
                        f"**Summary:**\n\n{aid_to_summary[r.aid]}\n")
            print(f"  {min(i + MAX_BATCH_ARTICLES, len(rows))}/{len(rows)} | {METER.line()}", flush=True)
    print(f"review file -> {review_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", nargs="*", default=["news"])
    ap.add_argument("--sample", type=int, default=0)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    try:
        if args.sample:
            quality_sample(args.sample)
        elif args.what and args.what[0] == "filings":
            summarize_filings()
        else:
            tickers = args.what[1:] if args.what and args.what[0] == "news" else args.what
            for t in (tickers or TICKERS):
                if not summarize_news_ticker(t):
                    break
    except QuotaExhausted as e:
        print(f"QUOTA EXHAUSTED ({e}) — checkpoints saved; rerun after the daily reset to resume.",
              flush=True)
    except BudgetStop as e:
        print(f"BUDGET STOP ({e}) — checkpoints saved; report to Dan before continuing.",
              flush=True)
    print(f"FINAL METER: {METER.line()}")
