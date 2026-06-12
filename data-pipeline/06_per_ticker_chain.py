"""Per-ticker pipeline chain (Dan's pipelining order, 2026-06-12).

Usage: python data-pipeline/06_per_ticker_chain.py TSLA

Steps (HARD RULE: refuses to run on a partial summary store):
  1. CERTIFY  — unique store rows == expected article count for the ticker,
                every article id covered, no empty summaries.
  2. ENV      — build env_data for this ticker (04_data_pipeline_v2.build_env_data:
                yfinance prices, summary CSV, summarized filings).
  3. SENTIMENT— FinBERT (finbert-tone, B7 name-based labels, CUDA) →
                data/03_model_input/<ticker>.pkl
  4. VALIDATE — step MarketEnvironment over the FULL window; then run the whole
                leakage suite (T1–T4, env-side trace armed) as a subprocess.
Exit 0 = ticker certified ready for its train run.
"""
import os
import sys
import json
import pickle
import subprocess
import importlib.util

import polars as pl

ROOT = os.getcwd()
INTER = os.path.join("data", "02_intermediate")
RAW = os.path.join("data", "01_raw")


def load_module(name, rel_path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def certify(ticker: str) -> int:
    """Store completeness certification. Returns expected article count."""
    src = pl.read_parquet(os.path.join(RAW, f"alpaca_news_{ticker}.parquet"))
    src = src.with_columns(pl.col("date").dt.date().alias("eff"))
    src = src.filter((pl.col("eff") >= pl.date(2025, 1, 1)) & (pl.col("eff") <= pl.date(2026, 6, 1)))
    src = src.with_columns(
        (pl.col("url") + "#" + pl.col("datetime").dt.strftime("%Y-%m-%dT%H:%M:%S")).alias("aid")
    ).unique(subset="aid")
    expected = set(src["aid"].to_list())

    store_path = os.path.join(INTER, f"summary_store_{ticker}.jsonl")
    assert os.path.exists(store_path), f"no summary store for {ticker}"
    got = {}
    with open(store_path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            got[r["article_id"]] = r["summary"]

    missing = expected - set(got)
    extra = set(got) - expected
    empty = [a for a, s in got.items() if not str(s).strip()]
    assert not missing, f"{ticker} NOT COMPLETE: {len(missing)} articles missing summaries"
    assert not empty, f"{ticker}: {len(empty)} empty summaries"
    if extra:
        print(f"  note: {len(extra)} store rows outside expected set (e.g. window-filtered) — ignored")
    csv_path = os.path.join(INTER, f"news_summary_{ticker}.csv")
    assert os.path.exists(csv_path), f"{ticker}: summary CSV not written"
    print(f"  CERTIFIED: {len(expected)} articles all summarized, CSV present")
    return len(expected)


def main(ticker: str):
    ticker = ticker.upper()
    print(f"[1/4] certifying {ticker} summary store")
    certify(ticker)

    print(f"[2/4] building env_data for {ticker}")
    m04 = load_module("m04", "data-pipeline/04_data_pipeline_v2.py")
    env_path = os.path.join(INTER, f"env_data_{ticker}.pkl")
    m04.build_env_data([ticker], out_path=env_path)

    print(f"[3/4] FinBERT sentiment -> model input pickle")
    m05 = load_module("m05", "data-pipeline/05_sentiment_v2.py")
    m05.INPUT_DIR = env_path
    with open(env_path, "rb") as f:
        env_data = pickle.load(f)
    sub = m05.subset_symbol_dict(env_data, ticker)
    m05.assign_finbert_scores(sub, ticker)
    out_pkl = os.path.join("data", "03_model_input", f"{ticker.lower()}.pkl")
    os.makedirs(os.path.dirname(out_pkl), exist_ok=True)
    with open(out_pkl, "wb") as f:
        pickle.dump(sub, f)
    print(f"  {len(sub)} dates -> {out_pkl}")

    print(f"[4/4] validation: MarketEnvironment full-window step + leakage suite")
    penv = load_module("penv", "puppy/environment.py")
    dates = sorted(sub)
    env = penv.MarketEnvironment(env_data_pkl=sub, start_date=dates[0], end_date=dates[-1], symbol=ticker)
    steps = 0
    while True:
        info = env.step()
        if info[-1]:
            break
        steps += 1
    assert steps == len(dates) - 1, f"stepped {steps}, expected {len(dates) - 1}"
    print(f"  stepped {steps} trading days {dates[0]} -> {dates[-1]}")

    r = subprocess.run([sys.executable, os.path.join("tests", "test_leakage.py")],
                       capture_output=True, text=True, encoding="utf-8")
    tail = "\n".join((r.stdout or "").strip().splitlines()[-3:])
    print(tail)
    assert r.returncode == 0, "leakage suite FAILED — train run blocked"
    print(f"{ticker} READY FOR TRAIN RUN (frozen config, window 2025-02-01..2025-12-31)")


if __name__ == "__main__":
    main(sys.argv[1])
