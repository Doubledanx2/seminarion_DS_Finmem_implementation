"""A3 canary (addendum, binding): ~10 gpt-4.1-mini calls (~30K tokens) through the
production path (puppy.chat.ChatOpenAICompatible + TokenMeter), then STOP.
Dan then checks platform.openai.com/usage: with the data-sharing free pool active,
billed cost must be $0.00. If real billing shows, the org Data Controls toggle
('Share inputs and outputs with OpenAI') is probably Disabled -> fix before any run.
"""
import os
import json
import importlib.util

import polars as pl
from dotenv import load_dotenv

load_dotenv()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

spec = importlib.util.spec_from_file_location("pchat", os.path.join(ROOT, "puppy", "chat.py"))
pchat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pchat)

chat = pchat.ChatOpenAICompatible(
    end_point="https://api.openai.com/v1/chat/completions",
    model="gpt-4.1-mini",  # EXACT string per A3.3 — free pool is per-model
    system_message="You are a helpful assistant.",
    other_parameters={"daily_token_budget": 2_400_000, "wait_for_reset": False},
)
endpoint = chat.guardrail_endpoint()

news = pl.read_parquet(os.path.join(ROOT, "data", "01_raw", "alpaca_news_TSLA.parquet"))
news = news.filter(pl.col("content").str.len_chars() > 2000).head(10)

ok = 0
for i, row in enumerate(news.iter_rows(named=True)):
    body = row["title"] + "\n" + row["content"][:8000]
    prompt = (
        "Based on the following news article about TSLA, respond ONLY with a JSON object "
        '{"investment_decision": "buy"|"sell"|"hold", "summary_reason": "<one sentence>"}.\n\n'
        + body
    )
    out = endpoint(prompt)
    try:
        parsed = json.loads(out)
        decision = parsed.get("investment_decision")
        valid = decision in ("buy", "sell", "hold")
    except json.JSONDecodeError:
        valid = False
        decision = out[:60]
    ok += valid
    print(f"[{i + 1}/10] decision={decision!r} valid_json={valid}")

meter = chat.meter.state
print(f"\nCANARY DONE: {ok}/10 valid JSON decisions")
print(f"tokens today: in={meter['in_tokens']:,} out={meter['out_tokens']:,} calls={meter['calls']}")
print("NOW: Dan checks platform.openai.com/usage -> billed cost must be $0.00 "
      "(complimentary/data-sharing tokens). Do NOT start real runs before that check.")
