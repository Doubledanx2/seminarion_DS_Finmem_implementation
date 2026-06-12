"""Stage-8 step 10: error-analysis pack — 20 random agent-days per ticker exported
for manual review (challenger principle). No API calls. Seed fixed for reproducibility."""
import os
import sys
import json
import pickle
import random

TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
OUT_DIR = os.path.join("data", "09_results", "error_pack")
random.seed(42)

os.makedirs(OUT_DIR, exist_ok=True)
for t in TICKERS:
    p = os.path.join("data", "07_test_model_output", f"{t}_ours", "agent_1", "state_dict.pkl")
    if not os.path.exists(p):
        print(f"{t}: test not complete - skipped")
        continue
    sd = pickle.load(open(p, "rb"))
    refl = {d: r for d, r in sd["reflection_result_series_dict"].items() if d.year == 2026}
    pf = sd["portfolio"]
    px = dict(zip(pf.date_series, pf.market_price_series))
    days_sorted = sorted(d for d in px if d.year == 2026)
    nxt = {d: days_sorted[i + 1] for i, d in enumerate(days_sorted[:-1])}
    sample = random.sample(sorted(refl), min(20, len(refl)))
    pack = []
    for d in sorted(sample):
        r = refl[d]
        ret = (px[nxt[d]] / px[d] - 1) * 100 if d in nxt and d in px else None
        pack.append({
            "date": str(d),
            "decision": r.get("investment_decision"),
            "raw_action": pf.action_series.get(d),
            "reasoning": r.get("summary_reason"),
            "cited_memory_ids": {k: r.get(k) for k in
                                 ("short_memory_index", "middle_memory_index",
                                  "long_memory_index", "reflection_memory_index")},
            "price": px.get(d),
            "next_day_return_pct": round(ret, 2) if ret is not None else None,
        })
    out = os.path.join(OUT_DIR, f"{t}_20days.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=1)
    print(f"{t}: 20 days -> {out}")
print("error pack complete")
