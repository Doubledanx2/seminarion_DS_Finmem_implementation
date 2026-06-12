# Stage-2 summarizer: Gemini 3.1 Flash-Lite (ARCHITECTURE.md final decision).
# Replaces the OpenAI path in 03_summarize_news_v2.py (kept for reference).
#
# Spec (claude_code_prompt_02_implementation.md step 2):
#   - batch multiple articles per request where quality allows (JSON-array output)
#   - body-less articles (~analyst one-liners) -> title+summary used directly, no API call
#   - free tier first: 30 RPM / 1,500 req/day -> paced + checkpointed across the
#     daily reset; rerun the script to resume (idempotent)
#   - token/cost meter printed continuously, persisted to data/02_intermediate/gemini_meter.json
#   - quality-sample mode: --sample N (default 50) summarizes N random articles and
#     writes a review file for Dan BEFORE any full run
#
# Usage:
#   python data-pipeline/03_summarize_gemini_v3.py --sample 50
#   python data-pipeline/03_summarize_gemini_v3.py news TSLA NFLX ...   (default: all)
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
import random
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


class Meter:
    def __init__(self):
        self.d = {"requests": 0, "in_tokens": 0, "out_tokens": 0}
        if os.path.exists(METER_PATH):
            with open(METER_PATH) as f:
                self.d = json.load(f)
        self.run_requests = 0
        self._last = 0.0

    def pace(self):
        wait = self._last + MIN_INTERVAL_S - time.time()
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    def add(self, usage):
        self.d["requests"] += 1
        self.run_requests += 1
        self.d["in_tokens"] += usage.prompt_token_count or 0
        self.d["out_tokens"] += usage.candidates_token_count or 0
        with open(METER_PATH, "w") as f:
            json.dump(self.d, f)

    @property
    def cost(self):
        return self.d["in_tokens"] / 1e6 * PRICE_IN + self.d["out_tokens"] / 1e6 * PRICE_OUT

    def line(self):
        return (f"req={self.d['requests']} in={self.d['in_tokens']:,} out={self.d['out_tokens']:,} "
                f"≈${self.cost:.2f} list-price (free tier: $0)")


METER = Meter()


def gemini_json(prompt: str, n_items: int, max_out: int) -> list[str]:
    """One paced Gemini call returning a JSON array of n_items strings."""
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
                    response_schema={"type": "ARRAY", "items": {"type": "STRING"}},
                ),
            )
            METER.add(resp.usage_metadata)
            out = json.loads(resp.text)
            if not isinstance(out, list) or len(out) != n_items:
                raise ValueError(f"expected {n_items} summaries, got {len(out) if isinstance(out, list) else type(out)}")
            return [str(s).strip() for s in out]
        except errors.APIError as e:
            if e.code in (429, 500, 503):
                sleep = 30 if e.code == 429 else 10
                print(f"  API {e.code}, retry in {sleep}s ({attempt + 1}/5)", flush=True)
                time.sleep(sleep)
            else:
                raise
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  bad JSON ({e}), retry ({attempt + 1}/5)", flush=True)
    raise RuntimeError("gemini_json: exhausted retries")


def build_body(title, summary, content) -> str:
    content_txt = TAG_RE.sub(" ", content or "").strip()
    parts = [p for p in [title, summary if summary and summary != title else "", content_txt] if p]
    return "\n".join(parts)[:MAX_BATCH_CHARS]


def fallback_summary(title, summary) -> str:
    return f"{title} {summary or ''}".strip()


def load_articles(ticker: str) -> pd.DataFrame:
    df = pl.read_parquet(os.path.join(RAW, f"alpaca_news_{ticker}.parquet")).to_pandas()
    df["body"] = [build_body(t, s, c) for t, s, c in zip(df["title"], df["summary"], df["content"])]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    # drop the stray out-of-window articles the API returned (see log)
    df = df[(df["date"] >= pd.Timestamp("2025-01-01").date())
            & (df["date"] <= pd.Timestamp("2026-06-01").date())].reset_index(drop=True)
    return df


def news_prompt(ticker: str, bodies: list[str]) -> str:
    head = (
        f"You are a financial news summarizer. Below are {len(bodies)} news articles about "
        f"{ticker}, separated by '=== ARTICLE k ==='. Summarize EACH article independently in at most "
        f"{SUMMARY_TOKENS} tokens, keeping concrete facts: numbers, analyst actions, price targets, "
        f"products, dates. No preamble. Return a JSON array with exactly {len(bodies)} strings, "
        f"one summary per article, in the same order."
    )
    blocks = [f"=== ARTICLE {i + 1} ===\n{b}" for i, b in enumerate(bodies)]
    return head + "\n\n" + "\n\n".join(blocks)


def summarize_news_ticker(ticker: str) -> bool:
    """Returns True if the ticker is fully summarized."""
    df = load_articles(ticker)
    ckpt_path = os.path.join(OUT, f"gemini_news_ckpt_{ticker}.jsonl")
    done: dict[str, str] = {}
    if os.path.exists(ckpt_path):
        with open(ckpt_path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                done[rec["url"]] = rec["summary"]
    ck = open(ckpt_path, "a", encoding="utf-8")

    def record(url, summary, how):
        done[url] = summary
        ck.write(json.dumps({"url": url, "summary": summary, "how": how}, ensure_ascii=False) + "\n")

    # 1. free fallbacks (no API)
    todo = []
    for row in df.itertuples():
        if row.url in done:
            continue
        if len(row.body) < BODYLESS_CHARS:
            record(row.url, fallback_summary(row.title, row.summary), "fallback")
        else:
            todo.append(row)
    ck.flush()
    print(f"[{ticker}] {len(df)} articles | {len(done) - len(todo) if False else len(done)} done "
          f"(incl. fallbacks) | {len(todo)} need Gemini", flush=True)

    # 2. batched API calls
    batch, batch_chars = [], 0
    full = True

    def flush_batch():
        nonlocal batch, batch_chars
        if not batch:
            return
        summaries = gemini_json(
            news_prompt(ticker, [r.body for r in batch]),
            n_items=len(batch),
            max_out=(SUMMARY_TOKENS + 60) * len(batch),
        )
        for r, s in zip(batch, summaries):
            record(r.url, s, "gemini")
        ck.flush()
        batch, batch_chars = [], 0

    for row in todo:
        if METER.run_requests >= MAX_REQ_PER_RUN:
            print(f"[{ticker}] daily request budget reached — resume after the 00:00 UTC quota reset",
                  flush=True)
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

    # 3. write final CSV when complete
    missing = [r.url for r in df.itertuples() if r.url not in done]
    if not missing:
        out = pd.DataFrame({
            "date": df["date"], "symbols": ticker, "summary": df["url"].map(done),
        }).sort_values("date")
        out_path = os.path.join(OUT, f"news_summary_{ticker}.csv")
        out.to_csv(out_path, index=False)
        print(f"[{ticker}] COMPLETE -> {out_path} | {METER.line()}", flush=True)
        return True
    print(f"[{ticker}] partial: {len(missing)} articles remain | {METER.line()}", flush=True)
    return False


def summarize_filings() -> None:
    df = pl.read_parquet(os.path.join(RAW, "filing_data.parquet")).to_pandas()
    ckpt_path = os.path.join(OUT, "gemini_filing_ckpt.jsonl")
    done = {}
    if os.path.exists(ckpt_path):
        with open(ckpt_path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                done[rec["url"]] = rec["summary"]
    with open(ckpt_path, "a", encoding="utf-8") as ck:
        for row in df.itertuples():
            if row.document_url in done:
                continue
            prompt = (
                f"Below is the MD&A section of a {row.type} filing by {row.ticker}. Summarize it in at "
                f"most {FILING_SUMMARY_TOKENS} tokens for a trading agent: revenue/profit drivers and "
                f"trends, guidance, margins, liquidity, risks, capital allocation. Concrete numbers over "
                f"prose. Return a JSON array with exactly 1 string.\n\n{row.content[:120_000]}"
            )
            s = gemini_json(prompt, n_items=1, max_out=FILING_SUMMARY_TOKENS + 100)[0]
            done[row.document_url] = s
            ck.write(json.dumps({"url": row.document_url, "summary": s}, ensure_ascii=False) + "\n")
            ck.flush()
            print(f"[filings] {row.ticker} {row.type} {str(row.est_timestamp)[:10]}: {len(s)} chars | {METER.line()}",
                  flush=True)
    out = df.copy()
    out["content"] = out["document_url"].map(done)
    out_path = os.path.join(RAW, "filing_data_summarized.parquet")
    pl.from_pandas(out).write_parquet(out_path)
    print(f"[filings] COMPLETE -> {out_path}")


def quality_sample(n: int) -> None:
    rows = []
    for t in TICKERS:
        df = load_articles(t)
        df = df[df["body"].str.len() >= BODYLESS_CHARS]
        k = max(2, n // len(TICKERS))
        rows.extend(df.sample(min(k, len(df)), random_state=42).assign(ticker=t).itertuples())
    rows = rows[:n]
    random.seed(42)
    print(f"quality sample: {len(rows)} articles")
    review_path = os.path.join(OUT, "gemini_quality_sample.md")
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(f"# Gemini {MODEL} quality sample — {len(rows)} articles\n")
        for i in range(0, len(rows), MAX_BATCH_ARTICLES):
            batch = rows[i:i + MAX_BATCH_ARTICLES]
            summaries = gemini_json(
                news_prompt(batch[0].ticker, [r.body for r in batch]),
                n_items=len(batch),
                max_out=(SUMMARY_TOKENS + 60) * len(batch),
            )
            for r, s in zip(batch, summaries):
                f.write(f"\n---\n## [{r.ticker}] {r.date} — {r.title}\n"
                        f"**Original ({len(r.body)} chars):**\n\n> {r.body[:600].replace(chr(10), ' ')}…\n\n"
                        f"**Gemini summary:**\n\n{s}\n")
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
        tickers = args.what[1:] if args.what[0] == "news" else args.what
        for t in (tickers or TICKERS):
            if not summarize_news_ticker(t):
                break
    print(f"FINAL METER: {METER.line()}")
