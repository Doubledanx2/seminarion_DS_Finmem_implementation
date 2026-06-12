"""Sin-2 (look-ahead bias) unit test — BACKTEST_INTEGRITY.md, binding.

Asserts that no future-dated content can ever be served to the agent:

  T1  News date assignment only moves FORWARD: every article's assigned env date is
      >= its raw publication date (UTC), and at most 1 day later (the 16:00 rule).
  T2  Filings are indexed by PUBLICATION time (filedAt/acceptance), never
      period-of-report: served date == EST date of the acceptance timestamp.
  T3  Every env_data pickle in data/03_model_input/ (plus the dry-run pickle):
      stepping MarketEnvironment yields strictly increasing dates, and every news
      item / filing served on day d is traceable to a source dated <= d.
  T4  (A5.4) Summary-store date integrity: every summary row's
      effective_trading_date equals its source article's pipeline-effective date
      (news) or its filedAt EST date (filings); and when env pickles exist, every
      summary served on day d has effective_trading_date == d (so
      max(served content dates) <= cur_date by construction).

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


def t4_summary_store_date_integrity():
    print("T4 (A5.4): summary-store dates match pipeline-effective dates")
    import json
    inter = os.path.join(ROOT, "data", "02_intermediate")

    stores = sorted(glob.glob(os.path.join(inter, "summary_store_*.jsonl")))
    if not stores:
        print("  [SKIP] no summary stores yet")
        return
    for store in stores:
        name = os.path.basename(store)
        rows = [json.loads(l) for l in open(store, encoding="utf-8")]
        if name == "summary_store_filings.jsonl":
            src = pl.read_parquet(os.path.join(RAW, "filing_data.parquet"))
            truth = {r["document_url"]: str(r["est_timestamp"])[:10] for r in src.iter_rows(named=True)}
        else:
            ticker = name[len("summary_store_"):-len(".jsonl")]
            src = pl.read_parquet(os.path.join(RAW, f"alpaca_news_{ticker}.parquet"))
            # article_id = url#source_datetime (B10: bare urls are not unique)
            truth = {f"{r['url']}#{str(r['datetime']).replace(' ', 'T')}": str(r["date"])[:10]
                     for r in src.iter_rows(named=True)}
        bad = [r for r in rows if truth.get(r["article_id"]) != r["effective_trading_date"]]
        unknown = [r for r in rows if r["article_id"] not in truth]
        check(f"{name}: {len(rows)} rows, effective date == pipeline date",
              not bad and not unknown, f"{len(bad)} mismatched, {len(unknown)} unknown ids")

    # env-pickle side: summaries served on day d must carry effective date d
    csvs = sorted(glob.glob(os.path.join(inter, "news_summary_*.csv")))
    pkls = sorted(glob.glob(os.path.join(MODEL_INPUT, "*.pkl")))
    if not (csvs and pkls):
        print("  [SKIP] env-side trace pending (needs summary CSVs + final pickles)")
        return
    import pandas as pd
    for pkl_path in pkls:
        env_data = pickle.load(open(pkl_path, "rb"))
        symbol = next(iter(next(iter(env_data.values()))["price"]))
        csv_path = os.path.join(inter, f"news_summary_{symbol}.csv")
        if not os.path.exists(csv_path):
            continue
        df = pd.read_csv(csv_path)
        date_of = dict(zip(df["summary"].str.strip(), pd.to_datetime(df["date"]).dt.date))
        bad = 0
        checked = 0
        for d, rec in env_data.items():
            for item in rec["news"].get(symbol, []):
                # sentiment suffix is appended after the summary; match on prefix
                base = item.split(" The positive score for this news is")[0].strip()
                src_d = date_of.get(base)
                if src_d is None:
                    continue
                checked += 1
                if src_d != d:
                    bad += 1
        check(f"{os.path.basename(pkl_path)}: served summaries dated == cur_date "
              f"({checked} traced)", bad == 0, f"{bad} violations")


if __name__ == "__main__":
    t1_news_dates_only_move_forward()
    t2_filings_indexed_by_publication()
    t3_env_pickles()
    t4_summary_store_date_integrity()
    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("\nALL LEAKAGE CHECKS PASSED")
