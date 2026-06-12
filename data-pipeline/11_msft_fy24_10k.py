"""Stage 8 item 2: MSFT FY2024 10-K (filed July 2024) — extract item 7 via sec-api
(1 credit) + Gemini-summarize, append to filing_data(_summarized).parquet."""
import os
import json
import datetime

import httpx
import polars as pl
from cleantext import clean
from dotenv import load_dotenv

load_dotenv()
RAW = os.path.join("data", "01_raw")

# 1. locate via free EDGAR
r = httpx.get("https://data.sec.gov/submissions/CIK0000789019.json",
              headers={"User-Agent": "MBA seminar project"}, timeout=30).json()
rec = r["filings"]["recent"]
cands = [(d, a, doc) for f, d, a, doc in zip(rec["form"], rec["filingDate"],
                                             rec["accessionNumber"], rec["primaryDocument"])
         if f == "10-K" and d < "2025-07-01"]
cands.sort(reverse=True)
fdate, acc, doc = cands[0]
url = f"https://www.sec.gov/Archives/edgar/data/789019/{acc.replace('-', '')}/{doc}"
print(f"MSFT most recent 10-K as of 2025-07-01: filed {fdate} -> {url}")

# 2. extract item 7 (1 sec-api credit)
resp = httpx.get("https://api.sec-api.io/extractor",
                 params={"url": url, "item": "7", "token": os.environ["SEC_KEY"]}, timeout=120)
resp.raise_for_status()
content = clean(resp.text, fix_unicode=True, to_ascii=True, lower=True, no_line_breaks=True)
print(f"extracted item 7: {len(content)} chars (sec-api credits now 31/100)")

# 3. Gemini summarize (same contract as 03_summarize_gemini_v3 filings)
from google import genai
from google.genai import types
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
prompt = ("Below is the MD&A section of a 10-K filing by MSFT.\n"
          "Rules (strict): use ONLY the text below — no background knowledge, no added "
          "context. Summarize in at most 400 tokens for a trading agent: revenue/profit "
          "drivers and trends, guidance, margins, liquidity, risks, capital allocation. "
          "Concrete numbers over prose. Return a JSON array with exactly one object "
          '{"id": "F1", "summary": "..."}.\n\n=== FILING id=F1 ===\n' + content[:120_000])
resp = client.models.generate_content(
    model="gemini-3.1-flash-lite", contents=prompt,
    config=types.GenerateContentConfig(
        temperature=0.2, max_output_tokens=520, response_mime_type="application/json",
        response_schema={"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "id": {"type": "STRING"}, "summary": {"type": "STRING"}}, "required": ["id", "summary"]}}))
summary = json.loads(resp.text)[0]["summary"].strip()
print(f"summary: {len(summary)} chars | tokens in/out: "
      f"{resp.usage_metadata.prompt_token_count}/{resp.usage_metadata.candidates_token_count}")

# 4. append to both parquets (raw content + summarized)
filed_dt = datetime.datetime.fromisoformat(fdate + "T16:00:00")
row = {"document_url": url, "ticker": "MSFT", "cik": "789019",
       "utc_timestamp": filed_dt, "est_timestamp": filed_dt, "type": "10-K"}
for path, text in [(os.path.join(RAW, "filing_data.parquet"), content),
                   (os.path.join(RAW, "filing_data_summarized.parquet"), summary)]:
    df = pl.read_parquet(path)
    if df.filter(pl.col("document_url") == url).height == 0:
        add = pl.DataFrame([{**row, "content": text}]).select(df.columns).cast(df.schema)
        pl.concat([df, add]).write_parquet(path)
        print(f"appended -> {path}")
    else:
        print(f"already present -> {path}")
