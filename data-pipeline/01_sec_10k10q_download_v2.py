# Adapted from 01_SEC_API_10k10q_download.py for the 2025-2026 reproduction window.
# Changes vs original (see IMPLEMENTATION_LOG.md):
#   1. Filing index comes from the FREE SEC EDGAR submissions API instead of
#      sec-api.io's Query API -> saves paid credits; only the Extractor API
#      (1 call per filing, single target section) spends credits.
#   2. Window/tickers parameterized at the top; output schema kept identical to the
#      original (document_url, content, ticker, cik, utc_timestamp, est_timestamp, type)
#      so 04-data_pipeline.py consumes it unchanged.
#
# COST: exactly one sec-api Extractor call per filing. Run 00_sec_filing_inventory.py
# first to see the count (30 filings for the 5 tickers in 2025-01-01..2026-06-01).
# DO NOT RUN without checking the remaining sec-api quota.

TICKERS = {
    "TSLA": 1318605,
    "NFLX": 1065280,
    "AMZN": 1018724,
    "MSFT": 789019,
    "COIN": 1679788,
}
START = "2025-01-01"
END = "2026-06-01"
TEN_K_SECTION = "7"          # MD&A, the paper's target section
TEN_Q_SECTION = "part1item2" # MD&A

import os
import time
import httpx
import pytz
import polars as pl
from cleantext import clean
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()
SEC_KEY = os.environ.get("SEC_KEY")
EXTRACTOR_URL = "https://api.sec-api.io/extractor"
EDGAR_HEADERS = {"User-Agent": "MBA seminar project dansh@university.example"}
OUT_PATH = os.path.join("data", "01_raw", "filing_data.parquet")


def edgar_index(ticker: str, cik: int) -> list[dict]:
    """List 10-K/10-Q filings in window from free EDGAR, with primary-document URLs."""
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    r = httpx.get(url, headers=EDGAR_HEADERS, timeout=30)
    r.raise_for_status()
    rec = r.json()["filings"]["recent"]
    out = []
    start, end = date.fromisoformat(START), date.fromisoformat(END)
    for form, fdate, acc, doc, acceptance in zip(
        rec["form"], rec["filingDate"], rec["accessionNumber"],
        rec["primaryDocument"], rec["acceptanceDateTime"],
    ):
        if form not in ("10-K", "10-Q"):
            continue
        if not (start <= date.fromisoformat(fdate) <= end):
            continue
        acc_nodash = acc.replace("-", "")
        out.append({
            "ticker": ticker,
            "cik": str(cik),
            "type": form,
            "document_url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}",
            # acceptanceDateTime is UTC, e.g. "2026-01-29T21:30:12.000Z"
            "utc_timestamp": datetime.fromisoformat(acceptance.rstrip("Z")),
        })
    return out


def extract_section(document_url: str, item: str) -> str | None:
    params = {"url": document_url, "item": item, "token": SEC_KEY}
    for attempt in range(3):
        r = httpx.get(EXTRACTOR_URL, params=params, timeout=120)
        if r.status_code == 200:
            return clean(r.text, fix_unicode=True, to_ascii=True, lower=True, no_line_breaks=True)
        if r.status_code == 429:
            time.sleep(15)
            continue
        print(f"FAILED {document_url} item={item}: HTTP {r.status_code} {r.text[:200]}")
        return None
    return None


def utc_to_est(dt: datetime) -> datetime:
    return pytz.UTC.localize(dt).astimezone(pytz.timezone("US/Eastern")).replace(tzinfo=None)


if __name__ == "__main__":
    filings = []
    for ticker, cik in TICKERS.items():
        filings.extend(edgar_index(ticker, cik))
        time.sleep(0.5)
    print(f"{len(filings)} filings to extract -> {len(filings)} sec-api credits")

    rows = []
    for i, f in enumerate(filings):
        section = TEN_K_SECTION if f["type"] == "10-K" else TEN_Q_SECTION
        content = extract_section(f["document_url"], section)
        print(f"[{i + 1}/{len(filings)}] {f['ticker']} {f['type']} {f['utc_timestamp'].date()} "
              f"-> {'ok, ' + str(len(content)) + ' chars' if content else 'FAILED'}")
        if content:
            rows.append({**f, "content": content, "est_timestamp": utc_to_est(f["utc_timestamp"])})
        time.sleep(1)

    df = pl.DataFrame(rows).select(
        ["document_url", "content", "ticker", "cik", "utc_timestamp", "est_timestamp", "type"]
    )
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df.write_parquet(OUT_PATH)
    print(f"Saved {df.height} filings -> {OUT_PATH}")
