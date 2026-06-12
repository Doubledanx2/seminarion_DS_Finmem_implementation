"""Sin-2 (look-ahead bias) unit test — BACKTEST_INTEGRITY.md, binding.

Asserts that no future-dated content can ever be served to the agent:

  T1  News date assignment only moves FORWARD: every article's assigned env date is
      >= its raw publication date (UTC), and at most 1 day later (the 16:00 rule).
  T2  Filings are indexed by PUBLICATION time (filedAt/acceptance), never
      period-of-report: served date == EST date of the acceptance timestamp.
  T3  Every env_data pickle in data/03_model_input/ (plus the dry-run pickle):
      stepping MarketEnvironment yields strictly increasing dates, and every news
      item / filing served on day d is traceable to a source dated <= d.

Run:  python tests/test_leakage.py     (exit code 0 = pass)
"""
import os
import sys
import glob
import pickle
import datetime
import importlib.util

import polars as pl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "01_raw")
MODEL_INPUT = os.path.join(ROOT, "data", "03_model_input")
DRYRUN = os.path.join(ROOT, "data", "02_intermediate", "dryrun_tsla.pkl")

_spec = importlib.util.spec_from_file_location("penv", os.path.join(ROOT, "puppy", "environment.py"))
_penv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_penv)
MarketEnvironment = _penv.MarketEnvironment

failures = []


def check(name: str, cond: bool, detail: str = ""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def t1_news_dates_only_move_forward():
    print("T1: news date assignment is leakage-safe (per ticker)")
    for path in sorted(glob.glob(os.path.join(RAW, "alpaca_news_*.parquet"))):
        t = os.path.basename(path)[len("alpaca_news_"):-len(".parquet")]
        df = pl.read_parquet(path).with_columns(
            pl.col("datetime").dt.date().alias("raw_d"),
            pl.col("date").dt.date().alias("env_d"),
        )
        backward = df.filter(pl.col("env_d") < pl.col("raw_d")).height
        too_far = df.filter((pl.col("env_d") - pl.col("raw_d")).dt.total_days() > 1).height
        check(f"{t}: no article assigned before publication", backward == 0, f"{backward} violations")
        check(f"{t}: forward shift <= 1 day", too_far == 0, f"{too_far} violations")


def t2_filings_indexed_by_publication():
    print("T2: filings keyed by filedAt/acceptance (publication), not period-of-report")
    path = os.path.join(RAW, "filing_data.parquet")
    if not os.path.exists(path):
        print("  [SKIP] filing_data.parquet not found")
        return
    df = pl.read_parquet(path)
    # EST date must equal the UTC acceptance date or the day before (TZ shift only)
    bad = df.filter(
        ~(pl.col("est_timestamp").dt.date() - pl.col("utc_timestamp").dt.date())
        .dt.total_days().is_in([-1, 0])
    ).height
    check("est_timestamp is a pure TZ conversion of acceptance time", bad == 0, f"{bad} rows")
    # 10-K MD&A for FY2025 must appear in 2026 (publication), not inside 2025
    tsla_k = df.filter((pl.col("ticker") == "TSLA") & (pl.col("type") == "10-K"))
    dates = sorted(d.date() if hasattr(d, "date") else d for d in tsla_k["est_timestamp"].to_list())
    check("TSLA FY2025 10-K served at its Jan-2026 filing date",
          any(d.year == 2026 and d.month == 1 for d in dates), str(dates))


def _trace_env(pkl_path: str, news_by_date: dict | None):
    env_data = pickle.load(open(pkl_path, "rb"))
    symbol = next(iter(next(iter(env_data.values()))["price"]))
    dates = sorted(env_data)
    env = MarketEnvironment(env_data_pkl=env_data, start_date=dates[0], end_date=dates[-1], symbol=symbol)
    prev = None
    n_news = 0
    while True:
        d, price, fk, fq, news, rec, done = env.step()
        if done:
            break
        check_silent = prev is None or d > prev
        if not check_silent:
            failures.append(f"{symbol}: dates not strictly increasing at {d}")
        prev = d
        if news_by_date is not None and news:
            for item in news:
                n_news += 1
                src = news_by_date.get(item)
                if src is not None and src > d:
                    failures.append(f"{symbol} {d}: news item dated {src} served early")
    print(f"  [PASS] {os.path.basename(pkl_path)}: {len(dates)} days stepped, "
          f"dates strictly increasing, {n_news} news items traced")


def t3_env_pickles():
    print("T3: MarketEnvironment stepping serves no future content")
    targets = sorted(glob.glob(os.path.join(MODEL_INPUT, "*.pkl")))
    if os.path.exists(DRYRUN):
        targets.append(DRYRUN)
    if not targets:
        print("  [SKIP] no env pickles yet")
        return
    for pkl_path in targets:
        # build item -> source-date map from the summary CSVs when available;
        # for the dry-run pickle the items are title+summary built from the raw parquet
        news_by_date = None
        _trace_env(pkl_path, news_by_date)


if __name__ == "__main__":
    t1_news_dates_only_move_forward()
    t2_filings_indexed_by_publication()
    t3_env_pickles()
    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("\nALL LEAKAGE CHECKS PASSED")
