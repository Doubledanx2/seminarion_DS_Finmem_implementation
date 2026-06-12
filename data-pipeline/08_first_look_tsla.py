"""Quick first-look at the TSLA test run (read-only, no tuning)."""
import os
import sys
import pickle
import importlib.util
from collections import Counter

import pandas as pd

sys.path.insert(0, os.getcwd())
import logging
logging.disable(logging.CRITICAL)
from puppy.agent import LLMAgent  # noqa: E402

agent = LLMAgent.load_checkpoint(path=os.path.join("data", "07_test_model_output", "TSLA", "agent_1"))
refl = agent.reflection_result_series_dict
test_days = {d: r for d, r in refl.items() if d.year == 2026}
decisions = {d: r.get("investment_decision", "hold") for d, r in test_days.items()}
print(f"test days with decisions: {len(decisions)}")
print("decision mix:", dict(Counter(decisions.values())))

pf = agent.portfolio
actions = {d: a for d, a in pf.action_series.items() if d.year == 2026}
prices = pd.Series(pf.market_price_series[-len(pf.date_series):], index=pf.date_series)
prices_2026 = prices[[d for d in prices.index if d.year == 2026]]

spec = importlib.util.spec_from_file_location("m7", os.path.join("data-pipeline", "07_metrics_v2.py"))
m7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m7)
dirs = pd.Series(actions).sort_index()
px = prices_2026.sort_index()
rep = m7.full_report(dirs, px, "TSLA-test", base_cost_bps=10)
for k in ("no_cost", "cost_10bps", "buy_and_hold"):
    m = rep[k]
    print(f"{k:12s}: CR={m['cum_return']*100:+.1f}%  Sharpe={m['sharpe']:.2f}  "
          f"MDD={m['max_drawdown']*100:.1f}%  vol={m['ann_vol']*100:.1f}%")
print(f"break-even vs B&H: {rep['break_even_bps_vs_bh']} bps | "
      f"Wilcoxon p={rep['wilcoxon_vs_bh_no_cost']['p_value']:.3f} | "
      f"Sharpe 95% CI {tuple(round(x, 2) for x in rep['bootstrap']['sharpe_ci_95'])}")
print("per-month:", {k: f"{v*100:+.1f}%" for k, v in rep["per_month"].items()})

with open(os.path.join("data", "07_test_model_output", "TSLA", "first_look.pkl"), "wb") as f:
    pickle.dump({"decisions": decisions, "report": rep}, f)
print("saved -> data/07_test_model_output/TSLA/first_look.pkl")
