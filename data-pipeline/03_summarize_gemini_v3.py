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
MIN_INTERVAL_S = 2.1                       # 30 RPM
MAX_REQ_PER_RUN = 1_450                    # free-tier daily headroom

import os
import re
import json
import time
import argparse
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
        self.last_usage = (0, 0)

    def pace(self):
        wait = self._last + MIN_INTERVAL_S - time.time()
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    def add(self, usage):
        self.d["requests"] += 1
        self.run_requests += 1
        pin = usage.prompt_token_count or 0
        pout = usage.candidates_token_count or 0
        self.last_usage = (pin, pout)
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


def gemini_call(prompt: str, schema: dict, max_out: int):
    """One paced, retried Gemini call with structured output."""
    METER.pace()
    for attempt in range(5):
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
            return json.loads(resp.text)
        except errors.APIError as e:
            if e.code in (429, 500, 503):
                sleep = 30 if e.code == 429 else 10
                print(f"  API {e.code}, retry in {sleep}s ({attempt + 1}/5)", flush=True)
                time.sleep(sleep)
            else:
                raise
        except json.JSONDecodeError as e:
            print(f"  bad JSON ({e}), retry ({attempt + 1}/5)", flush=True)
    raise RuntimeError("gemini_call: exhausted retries")


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


def summarize_batch(ticker: str, batch: list) -> dict[str, str]:
    """A5.2: send ID-tagged batch, parse per-ID. Returns url -> summary."""
    tags = {f"A{i + 1}": row for i, row in enumerate(batch)}
    out = gemini_call(
        news_prompt(ticker, [(aid, row.body) for aid, row in tags.items()]),
        schema=BATCH_SCHEMA,
        max_out=(SUMMARY_TOKENS + 80) * len(batch),
    )
    by_id = {str(o["id"]).strip(): str(o["summary"]).strip() for o in out if isinstance(o, dict)}
    missing = [aid for aid in tags if aid not in by_id or not by_id[aid]]
    if missing:
        raise ValueError(f"batch response missing ids: {missing}")
    return {tags[aid].aid: by_id[aid] for aid in tags}


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
    # URLs are shared by distinct articles — found via T4, see log B10)
    df["aid"] = df["url"] + "#" + df["source_datetime_utc"].astype(str)
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

    full = True
    batch, batch_chars = [], 0

    def flush_batch():
        nonlocal batch, batch_chars
        if not batch:
            return
        aid_to_summary = summarize_batch(ticker, batch)
        tin, tout = METER.last_usage
        per_in, per_out = tin // len(batch), tout // len(batch)  # even split, documented
        for row in batch:
            record(store_row(row, aid_to_summary[row.aid], "gemini", per_in, per_out))
        ck.flush()
        batch, batch_chars = [], 0

    for row in todo:
        if METER.run_requests >= MAX_REQ_PER_RUN:
            print(f"[{ticker}] daily request budget reached — rerun after 00:00 UTC reset", flush=True)
            full = False
            break
        if batch and (batch_chars + len(row.body) > MAX_BATCH_CHARS or len(batch) >= MAX_BATCH_ARTICLES):
            flush_batch()
            if METER.d["requests"] % 25 == 0:
                print(f"[{ticker}] {len(done)}/{len(df)} | {METER.line()}", flush=True)
        batch.append(row)
        batch_chars += len(row.body)
    if full:
        flush_batch()
    ck.close()

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
            out = gemini_call(prompt, BATCH_SCHEMA, FILING_SUMMARY_TOKENS + 120)
            s = str(out[0]["summary"]).strip()
            tin, tout = METER.last_usage
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
            aid_to_summary = summarize_batch(batch[0].ticker, batch)
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

    if args.sample:
        quality_sample(args.sample)
    elif args.what and args.what[0] == "filings":
        summarize_filings()
    else:
        tickers = args.what[1:] if args.what and args.what[0] == "news" else args.what
        for t in (tickers or TICKERS):
            if not summarize_news_ticker(t):
                break
    print(f"FINAL METER: {METER.line()}")
