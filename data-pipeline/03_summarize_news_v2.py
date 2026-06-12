# Adapted from 03-summary.py for the 2025-2026 reproduction (see IMPLEMENTATION_LOG.md).
# Changes vs original:
#   1. Original read CSVs with a 'body' column from the authors' private Refinitiv
#      dump at hardcoded /home/hfsladmin paths. This version reads our Alpaca
#      parquets (data/01_raw/alpaca_news_<TICKER>.parquet) and builds the article
#      body as headline + API summary + HTML-stripped content (handles the ~15%
#      of articles whose `content` is empty).
#   2. Output: one CSV per ticker at data/02_intermediate/news_summary_<TICKER>.csv
#      with the exact columns 04-data_pipeline.py expects: date, symbols, summary.
#   3. Row-level checkpointing (skips already-summarized rows on restart) instead of
#      rewriting the whole CSV inside a thread lock on every row.
#
# COST GATE: do not run before the estimate in 00_summary_cost_estimate.py is approved.

MODEL_NAME = "gpt-4.1-mini"  # pending user decision at the cost gate
SUMMARY_TOKEN_SIZE = 200     # paper default
MAX_PARALLEL = 8

import os
import re
import sys
import polars as pl
import pandas as pd
import concurrent.futures
from dotenv import load_dotenv
from model_wrapper import Model_Factory

load_dotenv()
TAG_RE = re.compile(r"<[^>]+>")
RAW_DIR = os.path.join("data", "01_raw")
OUT_DIR = os.path.join("data", "02_intermediate")


def build_body(title: str, summary: str, content: str) -> str:
    content_txt = TAG_RE.sub(" ", content or "").strip()
    parts = [p for p in [title, summary if summary != title else "", content_txt] if p]
    return "\n".join(parts)[:24000]  # hard cap ~6k tokens per article


def summarize_ticker(model, ticker: str) -> None:
    df = pl.read_parquet(os.path.join(RAW_DIR, f"alpaca_news_{ticker}.parquet")).to_pandas()
    df["body"] = [build_body(t, s, c) for t, s, c in zip(df["title"], df["summary"], df["content"])]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["symbols"] = ticker

    out_path = os.path.join(OUT_DIR, f"news_summary_{ticker}.csv")
    ckpt_path = os.path.join(OUT_DIR, f"news_summary_{ticker}.ckpt.csv")
    done = {}
    if os.path.exists(ckpt_path):
        prev = pd.read_csv(ckpt_path)
        done = dict(zip(prev["url"], prev["model_summary"]))
        print(f"[{ticker}] resuming: {len(done)} rows already summarized")

    todo = df[~df["url"].isin(done)]
    print(f"[{ticker}] {len(todo)} articles to summarize with {MODEL_NAME}")
    results = {}

    def work(row):
        return row.url, model.summarize(row.body, SUMMARY_TOKEN_SIZE)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL) as ex:
        futures = [ex.submit(work, row) for row in todo.itertuples()]
        for i, fut in enumerate(concurrent.futures.as_completed(futures)):
            url, s = fut.result()
            results[url] = s
            if (i + 1) % 100 == 0:
                merged = {**done, **results}
                pd.DataFrame({"url": list(merged), "model_summary": list(merged.values())}).to_csv(
                    ckpt_path, index=False)
                print(f"[{ticker}] {i + 1}/{len(todo)} (in={model.prompt_tokens} out={model.completion_tokens} tokens)",
                      flush=True)

    done.update(results)
    pd.DataFrame({"url": list(done), "model_summary": list(done.values())}).to_csv(ckpt_path, index=False)
    df["summary_out"] = df["url"].map(done)
    out = df[["date", "symbols", "summary_out"]].rename(columns={"summary_out": "summary"})
    out = out.dropna(subset=["summary"]).sort_values("date")
    out.to_csv(out_path, index=False)
    print(f"[{ticker}] saved {len(out)} summaries -> {out_path}")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    model = Model_Factory.create_model("chatgpt", key=os.environ["OPENAI_API_KEY"], model_name=MODEL_NAME)
    tickers = sys.argv[1:] or ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
    for t in tickers:
        summarize_ticker(model, t)
    print(f"TOTAL tokens: in={model.prompt_tokens} out={model.completion_tokens}")
