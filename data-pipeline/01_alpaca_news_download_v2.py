# Adapted from 01_Alpaca_News_API_download.py for the 2025-2026 reproduction window.
# Changes vs original (see IMPLEMENTATION_LOG.md):
#   1. Original paginated follow-up pages with `symbol=` (wrong param name, ignored by
#      the API) and without start/end -> follow-up pages returned unfiltered news.
#      Fixed: pagination repeats the full original query + page_token.
#   2. Original derived the query dates from a private price_data.parquet. Replaced
#      with an explicit ticker list + date window (calendar days, matching the paper's
#      one-query-per-day design and its 200-articles-per-day cap).
#   3. Added include_content=true so article bodies are available for summarization.
#   4. Resumable: one parquet per (ticker, day) in data/temp/alpaca/<ticker>/; days
#      already on disk are skipped. Final per-ticker parquet in data/01_raw/.
#   5. Original round_to_next_day could build an invalid date on month ends
#      (day + 1 overflow). Fixed with dt.offset_by.

TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
START_DATE = "2025-01-01"
END_DATE = "2026-06-01"  # inclusive
NUM_NEWS_PER_DAY_CAP = 200  # paper behavior
PAGE_LIMIT = 50
MAX_ATTEMPTS = 5
WAIT_TIME = 30

import os
import sys
import time
import httpx
import polars as pl
from dotenv import load_dotenv
from datetime import date, timedelta, datetime

load_dotenv()

ENDPOINT = "https://data.alpaca.markets/v1beta1/news"
HEADERS = {
    "Apca-Api-Key-Id": os.environ.get("ALPACA_KEY"),
    "Apca-Api-Secret-Key": os.environ.get("ALPACA_KEY_SECRET_KEY"),
}

RAW_DIR = os.path.join("data", "01_raw")
TEMP_DIR = os.path.join("data", "temp", "alpaca")

SCHEMA = {
    "author": pl.Utf8,
    "content": pl.Utf8,
    "datetime": pl.Datetime,
    "source": pl.Utf8,
    "summary": pl.Utf8,
    "title": pl.Utf8,
    "url": pl.Utf8,
}


def round_to_next_day(col: pl.Expr) -> pl.Expr:
    # paper logic: news time >= 16:00:00 (strictly later than 16:00 sharp) counts
    # toward the next trading morning 09:00
    cond = (col.dt.hour() >= 16) & ((col.dt.minute() > 0) | (col.dt.second() > 0))
    base = col.dt.date()
    shifted = pl.when(cond).then(base.dt.offset_by("1d")).otherwise(base)
    return shifted.dt.combine(pl.time(9, 0, 0))


def fetch_day(symbol: str, day: date) -> pl.DataFrame:
    """Fetch up to NUM_NEWS_PER_DAY_CAP articles for one symbol on one calendar day."""
    params = {
        "symbols": symbol,
        "start": day.strftime("%Y-%m-%d"),
        "end": (day + timedelta(days=1)).strftime("%Y-%m-%d"),
        "limit": PAGE_LIMIT,
        "include_content": "true",
    }
    rows = {k: [] for k in SCHEMA}
    page_token = None
    with httpx.Client(timeout=30) as client:
        while True:
            q = dict(params)
            if page_token:
                q["page_token"] = page_token
            for attempt in range(MAX_ATTEMPTS):
                resp = client.get(ENDPOINT, params=q, headers=HEADERS)
                if resp.status_code == 200:
                    break
                if resp.status_code == 429:
                    time.sleep(WAIT_TIME)
                else:
                    raise RuntimeError(f"{symbol} {day}: HTTP {resp.status_code}: {resp.text[:200]}")
            else:
                raise RuntimeError(f"{symbol} {day}: rate-limited after {MAX_ATTEMPTS} attempts")
            result = resp.json()
            for rec in result["news"]:
                rows["author"].append(rec.get("author"))
                rows["content"].append(rec.get("content"))
                rows["datetime"].append(datetime.fromisoformat(rec["created_at"].rstrip("Z")))
                rows["source"].append(rec.get("source"))
                rows["summary"].append(rec.get("summary"))
                rows["title"].append(rec.get("headline"))
                rows["url"].append(rec.get("url"))
            page_token = result.get("next_page_token")
            if not page_token or len(rows["datetime"]) >= NUM_NEWS_PER_DAY_CAP:
                break
    df = pl.DataFrame(rows, schema=SCHEMA).head(NUM_NEWS_PER_DAY_CAP)
    if df.height == 0:
        return df
    return df.with_columns(
        round_to_next_day(pl.col("datetime")).alias("date"),
        pl.lit(symbol).alias("equity"),
    )


def download_ticker(symbol: str, start: date, end: date) -> None:
    out_dir = os.path.join(TEMP_DIR, symbol)
    os.makedirs(out_dir, exist_ok=True)
    n_days = (end - start).days + 1
    t0 = time.time()
    for i in range(n_days):
        day = start + timedelta(days=i)
        path = os.path.join(out_dir, f"{day.isoformat()}.parquet")
        if os.path.exists(path):
            continue
        df = fetch_day(symbol, day)
        df.write_parquet(path)
        if (i + 1) % 50 == 0:
            print(f"[{symbol}] {i + 1}/{n_days} days, {time.time() - t0:.0f}s elapsed", flush=True)
    # combine
    files = sorted(os.listdir(out_dir))
    dfs = [pl.read_parquet(os.path.join(out_dir, f)) for f in files]
    dfs = [d for d in dfs if d.height > 0]
    combined = pl.concat(dfs)
    os.makedirs(RAW_DIR, exist_ok=True)
    combined.write_parquet(os.path.join(RAW_DIR, f"alpaca_news_{symbol}.parquet"))
    print(f"[{symbol}] DONE: {combined.height} articles -> {RAW_DIR}/alpaca_news_{symbol}.parquet", flush=True)
    # monthly counts report
    monthly = (
        combined.with_columns(pl.col("datetime").dt.strftime("%Y-%m").alias("month"))
        .group_by("month").len().sort("month")
    )
    print(monthly.to_pandas().to_string(index=False), flush=True)


if __name__ == "__main__":
    tickers = sys.argv[1:] or TICKERS
    start = date.fromisoformat(START_DATE)
    end = date.fromisoformat(END_DATE)
    for t in tickers:
        download_ticker(t, start, end)
