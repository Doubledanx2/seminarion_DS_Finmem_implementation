"""Count 10-K/10-Q filings per ticker in the window using the FREE SEC EDGAR
submissions API (no sec-api.io credits spent). Used to plan the exact number of
sec-api Extractor calls before asking for approval."""
import httpx
from datetime import date

CIKS = {
    "TSLA": 1318605,
    "NFLX": 1065280,
    "AMZN": 1018724,
    "MSFT": 789019,
    "COIN": 1679788,
}
START, END = date(2025, 1, 1), date(2026, 6, 1)
HEADERS = {"User-Agent": "MBA seminar project dansh@university.example"}

total = 0
for ticker, cik in CIKS.items():
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    r = httpx.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    recent = r.json()["filings"]["recent"]
    rows = list(zip(recent["form"], recent["filingDate"], recent["accessionNumber"], recent["primaryDocument"]))
    in_window = [
        (f, d) for f, d, _, _ in rows
        if f in ("10-K", "10-Q") and START <= date.fromisoformat(d) <= END
    ]
    ks = [d for f, d in in_window if f == "10-K"]
    qs = [d for f, d in in_window if f == "10-Q"]
    print(f"{ticker}: {len(ks)} x 10-K {ks} | {len(qs)} x 10-Q {qs}")
    total += len(in_window)
print(f"TOTAL filings in window: {total}")
print(f"Extractor calls needed (1 section each: 10-K item 7, 10-Q part1item2): {total}")
