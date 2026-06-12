# Adapted from 04-data_pipeline.py (see IMPLEMENTATION_LOG.md).
# Changes vs original:
#   1. Paths parameterized to this repo's data/ layout (original used /home/yyu/YJ/...).
#   2. Tickers/dates set for the 2025-26 reproduction (original had a different
#      6-ticker experiment: BAC, DIS, GM, MRNA, NVDA, PFE).
#   3. yfinance >= 0.2.x: auto_adjust defaults to True and 'Adj Close' no longer
#      exists -> original KeyError. We request auto_adjust=True and use 'Close'
#      (which is then the adjusted close, what the paper used).
#   4. Filing parquet comes from 01_sec_10k10q_download_v2.py output; news CSVs
#      from 03_summarize_news_v2.py output.
#   5. Original env_data combined only dates present in the *price* dict (trading
#      days) -> weekend/holiday news silently dropped, exactly as in the paper.
#      Kept for comparability (documented as a data-quality note).

import os
import glob
import pickle
import pandas as pd
import yfinance as yf
from typing import List

BASE = os.path.join("data", "02_intermediate")
RAW = os.path.join("data", "01_raw")
START_DAY = "2025-01-01"
END_DAY = "2026-06-02"  # yfinance end is exclusive; covers through 2026-06-01
TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]


def download_price(tickers: List[str]) -> List[pd.DataFrame]:
    df_list = []
    for ticker in tickers:
        print(f"Downloading price data for {ticker}")
        data = yf.download(ticker, start=START_DAY, end=END_DAY, auto_adjust=True, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data.reset_index()
        data["Date"] = data["Date"].dt.date
        data = data[["Date", "Close"]].rename(columns={"Date": "date", "Close": ticker})
        df_list.append(data)
    return df_list


def combine_price(df_list: List[pd.DataFrame], tickers: List[str]) -> dict:
    df_dicts = [dict(zip(df["date"], df[t])) for df, t in zip(df_list, tickers)]
    combined = {d: {"price": {}} for dd in df_dicts for d in dd}
    for i, dd in enumerate(df_dicts):
        for d, p in dd.items():
            combined[d]["price"][tickers[i]] = float(p)
    with open(os.path.join(BASE, "price.pkl"), "wb") as f:
        pickle.dump(combined, f)
    print(f"price.pkl: {len(combined)} trading days")
    return combined


def create_news_dict() -> dict:
    combined = {}
    for file in glob.glob(os.path.join(BASE, "news_summary_*.csv")):
        df = pd.read_csv(file)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        symbol = df.at[0, "symbols"]
        for d, summaries in df.groupby("date")["summary"].apply(list).items():
            combined.setdefault(d, {"news": {}})["news"][symbol] = summaries
    with open(os.path.join(BASE, "news.pkl"), "wb") as f:
        pickle.dump(combined, f)
    print(f"news.pkl: {len(combined)} dates")
    return combined


def process_filing_data() -> tuple:
    start, end = pd.to_datetime(START_DAY), pd.to_datetime(END_DAY)
    fk = pd.read_parquet(os.path.join(RAW, "filing_data.parquet"))
    fk = fk.drop(columns=["document_url", "cik", "utc_timestamp"])
    fk = fk.rename(columns={"est_timestamp": "date"})[["date", "ticker", "content", "type"]]
    fk["date"] = pd.to_datetime(pd.to_datetime(fk["date"]).dt.date)
    fk = fk[fk["ticker"].isin(TICKERS)]
    out = {}
    for form, key in [("10-K", "filing_k"), ("10-Q", "filing_q")]:
        sub = fk[(fk["type"] == form) & (fk["date"] >= start) & (fk["date"] <= end)].sort_values("date")
        sub = sub.copy()
        sub["date"] = sub["date"].dt.date
        out[key] = {d: {key: g.set_index("ticker")["content"].to_dict()}
                    for d, g in sub.groupby("date")}
    with open(os.path.join(BASE, "filing_k.pkl"), "wb") as f:
        pickle.dump(out["filing_k"], f)
    with open(os.path.join(BASE, "filing_q.pkl"), "wb") as f:
        pickle.dump(out["filing_q"], f)
    print(f"filing_k.pkl: {len(out['filing_k'])} dates | filing_q.pkl: {len(out['filing_q'])} dates")
    return out["filing_q"], out["filing_k"]


if __name__ == "__main__":
    price = combine_price(download_price(TICKERS), TICKERS)
    news = create_news_dict()
    q, k = process_filing_data()

    for d in price:
        q.setdefault(d, {"filing_q": {}})
        k.setdefault(d, {"filing_k": {}})
        news.setdefault(d, {"news": {t: [] for t in TICKERS}})
    for d in news:
        for t in TICKERS:
            news[d]["news"].setdefault(t, [])

    q, k = dict(sorted(q.items())), dict(sorted(k.items()))
    env_data = {d: (price[d], news[d], q[d], k[d]) for d in sorted(price)}
    with open(os.path.join(BASE, "env_data.pkl"), "wb") as f:
        pickle.dump(env_data, f)
    print(f"env_data.pkl: {len(env_data)} trading days saved to {BASE}")
