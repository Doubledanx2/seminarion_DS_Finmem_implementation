"""Zero-cost plumbing check (Stage 1 validation, run before any paid step).

Builds a TSLA env-data pickle in the exact final format using REAL Alpaca news
(headline+summary as a stand-in for the GPT summaries) and REAL yfinance prices,
with empty filings, then instantiates puppy.MarketEnvironment and steps it.
Catches format/integration bugs without spending OpenAI/sec-api credits.
"""
import os
import sys
import pickle
import pandas as pd
import polars as pl
import yfinance as yf

# import environment.py directly: importing the puppy package pulls in faiss,
# which is only needed for the trading stage
import importlib.util

_spec = importlib.util.spec_from_file_location("penv", os.path.join("puppy", "environment.py"))
_penv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_penv)
MarketEnvironment = _penv.MarketEnvironment

TICKER = "TSLA"

# 1. prices (adjusted close)
px = yf.download(TICKER, start="2025-01-01", end="2026-06-02", auto_adjust=True, progress=False)
if isinstance(px.columns, pd.MultiIndex):
    px.columns = px.columns.get_level_values(0)
px = px.reset_index()
px["date"] = px["Date"].dt.date
price_by_date = dict(zip(px["date"], px["Close"].astype(float)))
print(f"prices: {len(price_by_date)} trading days, {min(price_by_date)} -> {max(price_by_date)}")

# 2. news placeholder summaries by rounded date
news = pl.read_parquet(os.path.join("data", "01_raw", f"alpaca_news_{TICKER}.parquet"))
news = news.with_columns(pl.col("date").dt.date().alias("d"))
news_by_date = {
    d: [f"{t}. {s}" if s and s != t else f"{t}." for t, s in zip(g["title"], g["summary"])]
    for d, g in news.group_by("d", maintain_order=True)
}
news_by_date = {(k[0] if isinstance(k, tuple) else k): v for k, v in news_by_date.items()}

# 3. final per-ticker structure over trading days (paper behavior: trading days only)
env = {
    d: {
        "price": {TICKER: p},
        "filing_k": {},
        "filing_q": {},
        "news": {TICKER: news_by_date.get(d, [])},
    }
    for d, p in price_by_date.items()
}
out = os.path.join("data", "02_intermediate", f"dryrun_{TICKER.lower()}.pkl")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "wb") as f:
    pickle.dump(env, f)

# 4. validate + step
dates = sorted(env)
me = MarketEnvironment(env_data_pkl=env, start_date=dates[0], end_date=dates[-1], symbol=TICKER)
print(f"MarketEnvironment OK, simulation_length={me.simulation_length}")
for _ in range(5):
    d, p, fk, fq, nws, rec, done = me.step()
    print(f"  {d} price={p:.2f} news={len(nws)} filing_k={'Y' if fk else '-'} record={rec:+.2f} done={done}")
weekend_news = sum(len(v) for k, v in news_by_date.items() if k not in price_by_date)
total_news = sum(len(v) for v in news_by_date.values())
print(f"news dropped on non-trading days (paper behavior): {weekend_news}/{total_news}")
