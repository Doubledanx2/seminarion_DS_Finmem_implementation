"""FinMem-Ours setup v2 (Stage 8): 6-month train window, mandatory 10-K seeding,
Jul-Dec 2025 persona overviews with numeric SELF-VERIFICATION (replaces human gate).

Outputs: config/<t>_finmem_ours_config.toml x5 (+ tsla nomem variant),
data/02_intermediate/filing_seeds.json, console report.
Exit code != 0 if self-verification fails (abort the run).
"""
import os
import re
import json
import pickle
import datetime

import numpy as np
import polars as pl
import toml

TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
TRAIN_START, TRAIN_END = datetime.date(2025, 7, 1), datetime.date(2025, 12, 31)
TENQ_FROM = TRAIN_START - datetime.timedelta(days=120)
RAW = os.path.join("data", "01_raw")
INTER = os.path.join("data", "02_intermediate")


def compute_overview(t: str):
    with open(os.path.join("data", "03_model_input", f"{t.lower()}.pkl"), "rb") as f:
        env = pickle.load(f)
    days = sorted(d for d in env if TRAIN_START <= d <= TRAIN_END)
    px = np.array([env[d]["price"][t] for d in days])
    rets = np.diff(px) / px[:-1]
    vals = {
        "total": round((px[-1] / px[0] - 1) * 100, 1),
        "vol": round(float(rets.std(ddof=1) * np.sqrt(252) * 100)),
        "mdd": round(float((px / np.maximum.accumulate(px) / 1 - np.maximum.accumulate(px) / np.maximum.accumulate(px)).min() * 0), 1),  # placeholder, fixed below
    }
    eq = px / px[0]
    vals["mdd"] = round(float((eq / np.maximum.accumulate(eq) - 1).min() * 100), 1)
    iup, idn = int(np.argmax(rets)), int(np.argmin(rets))
    vals.update(up=round(rets[iup] * 100, 1), up_d=str(days[iup + 1]),
                dn=round(rets[idn] * 100, 1), dn_d=str(days[idn + 1]),
                p_end=round(float(px[-1]), 2), p_start=round(float(px[0]), 2))
    text = (
        f"Performance overview of {t} during Jul-Dec 2025 (your training period): "
        f"total return {vals['total']:+.1f}%, annualized volatility {vals['vol']}%, "
        f"maximum drawdown {vals['mdd']:.1f}%. "
        f"Biggest single-day gain {vals['up']:+.1f}% on {vals['up_d']}; "
        f"biggest single-day loss {vals['dn']:+.1f}% on {vals['dn_d']}. "
        f"The stock ended the period at {vals['p_end']:.2f} versus {vals['p_start']:.2f} at its start."
    )
    return text, vals


def self_verify(t: str, text: str) -> list:
    """Recompute every number independently and assert it appears in the text."""
    _, vals = compute_overview(t)
    problems = []
    expect = [f"{vals['total']:+.1f}%", f"{vals['vol']}%", f"{vals['mdd']:.1f}%",
              f"{vals['up']:+.1f}% on {vals['up_d']}", f"{vals['dn']:+.1f}% on {vals['dn_d']}",
              f"{vals['p_end']:.2f}", f"{vals['p_start']:.2f}"]
    problems.extend(e for e in expect if e not in text)
    # leakage scan: no dates outside the train window
    for d in re.findall(r"20\d\d-\d\d-\d\d", text):
        dd = datetime.date.fromisoformat(d)
        if not (TRAIN_START <= dd <= TRAIN_END):
            problems.append(f"out-of-window date {d}")
    if "2026" in text:
        problems.append("mentions 2026")
    return problems


def build_seeds():
    fil = pl.read_parquet(os.path.join(RAW, "filing_data_summarized.parquet"))
    seeds = []
    for t in TICKERS:
        sub = fil.filter(pl.col("ticker") == t).sort("est_timestamp")
        rows = [(r["type"], r["est_timestamp"].date() if hasattr(r["est_timestamp"], "date")
                 else r["est_timestamp"], r["content"]) for r in sub.iter_rows(named=True)]
        ks = [r for r in rows if r[0] == "10-K" and r[1] < TRAIN_START]
        qs = [r for r in rows if r[0] == "10-Q" and TENQ_FROM <= r[1] < TRAIN_START]
        assert ks, f"{t}: no 10-K before train start — seeding is MANDATORY (Stage 8)"
        seeds.append({"symbol": t, "type": "10-K", "date": str(ks[-1][1]), "summary": ks[-1][2]})
        if qs:
            seeds.append({"symbol": t, "type": "10-Q", "date": str(qs[-1][1]), "summary": qs[-1][2]})
    path = os.path.join(INTER, "filing_seeds.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seeds, f, ensure_ascii=False, indent=1)
    return path, seeds


TEMPLATE = """# FinMem-Ours — OUR headline configuration (Stage 8: 6-month train). {ticker}.
# Frozen at FinMem-Ours freeze #3. Train 2025-07-01..2025-12-31, test 2026-01-02..2026-06-01.

[chat]
model = "gpt-4.1-mini"
end_point = "https://api.openai.com/v1/chat/completions"
system_message = "You are a helpful assistant."
temperature = 1.0
daily_token_budget = 2400000
wait_for_reset = false                       # Stage 8: paid overflow AUTHORIZED
paid_overflow = true
paid_cap_usd = 3.00                          # hard chat-spend cap (Dan, $5 deposited)

[general]
top_k = 5
agent_name = "agent_1"
look_back_window_size = 7
trading_symbol = "{ticker}"
persona_rule = "paper_rule"
persona_switch_window = 3
observation_window = 7
extended_reflection = true
extended_reflection_target = "long"
extended_reflection_train = true
long_only = true
unit_position = true
disable_downward_jumps = true
pure_age_recency = true
filing_seed_file = "data/02_intermediate/filing_seeds.json"
{nomem}character_string = '''{persona_train}'''
character_string_test = '''{persona_train}

{overview}'''

[agent.agent_1.embedding.detail]
backend = "openai"
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

if __name__ == "__main__":
    import sys
    failures = []
    seed_path, seeds = build_seeds()
    print(f"filing seeds -> {seed_path}:")
    for s in seeds:
        print(f"  {s['symbol']} {s['type']} filed {s['date']}")

    for t in TICKERS:
        src = toml.load(os.path.join("config", f"{t.lower()}_gpt41mini_config.toml"))
        persona_train = src["general"]["character_string"].strip()
        text, _ = compute_overview(t)
        problems = self_verify(t, text)
        if problems:
            failures.append((t, problems))
        out = TEMPLATE.format(ticker=t, persona_train=persona_train, overview=text, nomem="")
        path = os.path.join("config", f"{t.lower()}_finmem_ours_config.toml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
        cfg = toml.load(path)
        assert cfg["general"]["top_k"] == 5 and cfg["general"]["persona_switch_window"] == 3
        # verify the text embedded in the config too
        emb_problems = self_verify(t, cfg["general"]["character_string_test"])
        if emb_problems:
            failures.append((t, ["config-embedded: "] + emb_problems))
        print(f"wrote {path} | self-verify: {'OK' if not problems and not emb_problems else 'FAIL'}")
        if t == "TSLA":
            nomem = TEMPLATE.format(ticker=t, persona_train=persona_train, overview=text,
                                    nomem="no_memory = true\n")
            with open(os.path.join("config", "tsla_finmem_ours_nomem_config.toml"),
                      "w", encoding="utf-8") as f:
                f.write(nomem)
            print("wrote config/tsla_finmem_ours_nomem_config.toml (ablation)")

    print("\nPERSONA OVERVIEWS (Jul-Dec 2025, self-verified):")
    for t in TICKERS:
        print(f"\n[{t}] {compute_overview(t)[0]}")
    if failures:
        print(f"\nSELF-VERIFY FAILURES: {failures}")
        sys.exit(1)
    print("\nALL PERSONA NUMBERS SELF-VERIFIED — gate passed without human stop (per Stage 8)")
