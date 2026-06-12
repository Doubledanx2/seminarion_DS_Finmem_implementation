"""FinMem-Ours setup (Stage 7 §1): per-ticker configs, train-period persona
overviews (from OUR price data), filing seeds, and the boundary-gap audit.

Outputs:
  config/<t>_finmem_ours_config.toml  x5
  data/02_intermediate/filing_seeds.json
  console report: overviews (for Dan's leakage glance) + boundary-gap counts
"""
import os
import json
import pickle
import datetime

import httpx
import numpy as np
import polars as pl

TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
TRAIN_START, TRAIN_END = datetime.date(2025, 2, 1), datetime.date(2025, 12, 31)
SEED_FROM = datetime.date(2024, 11, 3)   # 90 days before train start
RAW = os.path.join("data", "01_raw")
INTER = os.path.join("data", "02_intermediate")

# ---------- 1. train-period overview per ticker (OUR price data only) ----------
overviews = {}
for t in TICKERS:
    with open(os.path.join("data", "03_model_input", f"{t.lower()}.pkl"), "rb") as f:
        env = pickle.load(f)
    days = sorted(d for d in env if TRAIN_START <= d <= TRAIN_END)
    px = np.array([env[d]["price"][t] for d in days])
    rets = np.diff(px) / px[:-1]
    total = px[-1] / px[0] - 1
    vol = rets.std(ddof=1) * np.sqrt(252)
    eq = px / px[0]
    mdd = (eq / np.maximum.accumulate(eq) - 1).min()
    iup, idn = int(np.argmax(rets)), int(np.argmin(rets))
    overviews[t] = (
        f"Performance overview of {t} during Feb-Dec 2025 (your training period): "
        f"total return {total * 100:+.1f}%, annualized volatility {vol * 100:.0f}%, "
        f"maximum drawdown {mdd * 100:.1f}%. "
        f"Biggest single-day gain {rets[iup] * 100:+.1f}% on {days[iup + 1]}; "
        f"biggest single-day loss {rets[idn] * 100:+.1f}% on {days[idn + 1]}. "
        f"The stock ended the period at {px[-1]:.2f} versus {px[0]:.2f} at its start."
    )

# ---------- 2. filing seeds from existing data ----------
fil = pl.read_parquet(os.path.join(RAW, "filing_data_summarized.parquet"))
seeds = []
for r in fil.iter_rows(named=True):
    filed = r["est_timestamp"].date() if hasattr(r["est_timestamp"], "date") else r["est_timestamp"]
    if SEED_FROM <= filed < TRAIN_START:
        seeds.append({"symbol": r["ticker"], "type": r["type"],
                      "date": str(filed), "summary": r["content"]})
seed_path = os.path.join(INTER, "filing_seeds.json")
with open(seed_path, "w", encoding="utf-8") as f:
    json.dump(seeds, f, ensure_ascii=False, indent=1)

# ---------- 3. boundary-gap audit via free EDGAR ----------
CIKS = {"TSLA": 1318605, "NFLX": 1065280, "AMZN": 1018724, "MSFT": 789019, "COIN": 1679788}
gap = {}
for t, cik in CIKS.items():
    r = httpx.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json",
                  headers={"User-Agent": "MBA seminar project"}, timeout=30).json()
    rec = r["filings"]["recent"]
    in_window = [(f, d) for f, d in zip(rec["form"], rec["filingDate"])
                 if f in ("10-K", "10-Q") and SEED_FROM <= datetime.date.fromisoformat(d) < TRAIN_START]
    have = {(s["type"], s["date"]) for s in seeds if s["symbol"] == t}
    missing = [fd for fd in in_window if fd not in have]
    gap[t] = {"in_90d_window": in_window, "seeded": sorted(have), "missing_from_our_data": missing}

# ---------- 4. write the 5 configs ----------
TEMPLATE = """# FinMem-Ours — OUR headline configuration (Stage 7). {ticker}.
# Paper architecture + all our fixes. Frozen at the FinMem-Ours freeze commit.

[chat]
model = "gpt-4.1-mini"
end_point = "https://api.openai.com/v1/chat/completions"
system_message = "You are a helpful assistant."
temperature = 1.0
daily_token_budget = 2400000
wait_for_reset = true

[general]
top_k = 5
agent_name = "agent_1"
look_back_window_size = 7
trading_symbol = "{ticker}"
persona_rule = "paper_rule"                  # two-sided risk persona (paper section 3.1)
persona_switch_window = 3                    # "such as three days"
observation_window = 7                       # M-day cumulative return in test prompt
extended_reflection = true                   # paper-described M-day self-review
extended_reflection_target = "long"          # deep layer - safe: downward jumps disabled
extended_reflection_train = true             # both phases
long_only = true
unit_position = true                         # holdings in {{0, +1}}
disable_downward_jumps = true                # F2 fix: deep retention
pure_age_recency = true                      # no recency reset on promotion (F2 echo fix)
filing_seed_file = "data/02_intermediate/filing_seeds.json"
character_string = '''{persona_train}'''
character_string_test = '''{persona_train}

{overview}'''

[agent.agent_1.embedding.detail]
backend = "openai"                           # ada-002 per Stage-7 (pre-approved ~$1.50)
embedding_model = "text-embedding-ada-002"
chunk_size = 5000
verbose = false

[short]
importance_score_initialization = "sample"
decay_params = {{recency_factor=14.0, importance_factor=0.92}}
clean_up_threshold_dict = {{recency_threshold=0.05, importance_threshold=5}}
jump_threshold_upper = 60

[mid]
jump_threshold_lower = 60
jump_threshold_upper = 80
importance_score_initialization = "sample"
decay_params = {{recency_factor=90.0, importance_factor=0.967}}
clean_up_threshold_dict = {{recency_threshold=0.05, importance_threshold=5}}

[long]
jump_threshold_lower = 80
importance_score_initialization = "sample"
decay_params = {{recency_factor=365.0, importance_factor=0.988}}
clean_up_threshold_dict = {{recency_threshold=0.05, importance_threshold=5}}

[reflection]
importance_score_initialization = "sample"
decay_params = {{recency_factor=365.0, importance_factor=0.988}}
clean_up_threshold_dict = {{recency_threshold=0.05, importance_threshold=5}}
"""

import re
import toml
for t in TICKERS:
    src = toml.load(os.path.join("config", f"{t.lower()}_gpt41mini_config.toml"))
    persona_train = src["general"]["character_string"].strip()
    out = TEMPLATE.format(ticker=t, persona_train=persona_train, overview=overviews[t])
    path = os.path.join("config", f"{t.lower()}_finmem_ours_config.toml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    cfg = toml.load(path)  # validate parse
    assert cfg["general"]["top_k"] == 5 and cfg["general"]["persona_switch_window"] == 3
    print(f"wrote {path}")

print(f"\nfiling seeds -> {seed_path}: {[(s['symbol'], s['type'], s['date']) for s in seeds]}")
print("\nBOUNDARY-GAP AUDIT (filings filed in the 90d pre-train window):")
for t, g in gap.items():
    print(f"  {t}: in-window={g['in_90d_window']} | seeded={g['seeded']} | MISSING={g['missing_from_our_data']}")
print("\nPERSONA OVERVIEWS (for Dan's 60-second leakage glance — test prompts only):")
for t in TICKERS:
    print(f"\n[{t}] {overviews[t]}")
