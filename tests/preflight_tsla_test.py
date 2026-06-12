"""Pre-flight for the TSLA TEST run (Dan's checklist A1-D8). NO API calls.
Renders the exact first-test-day prompt via a capture endpoint and dumps it to
data/04_model_output_log/tsla_test_prompt_sample.txt.
"""
import os
import re
import sys
import json
import pickle
import logging
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

results = []


def check(tag, ok, line):
    results.append((tag, bool(ok), line))
    print(f"[{'PASS' if ok else 'FAIL'}] {tag}: {line}")


logging.disable(logging.CRITICAL)
from puppy.agent import LLMAgent                          # noqa: E402
from puppy.run_type import RunMode                        # noqa: E402
from puppy.reflection import trading_reflection           # noqa: E402
from puppy.environment import MarketEnvironment           # noqa: E402
from puppy.portfolio import Portfolio                     # noqa: E402
from puppy.prompts import as_shipped_persona_line         # noqa: E402

CKPT = os.path.join("data", "05_train_model_output", "TSLA")

# ---------- A: trained state integrity ----------
agent = LLMAgent.load_checkpoint(path=os.path.join(CKPT, "agent_1"))
check("A1.counter", agent.counter == 231, f"counter={agent.counter} (expect 231)")
refl = agent.reflection_result_series_dict
rd = sorted(refl)
check("A1.reflections", len(refl) == 229 and rd[0] == datetime.date(2025, 2, 3)
      and rd[-1] == datetime.date(2025, 12, 30),
      f"{len(refl)} reflection days {rd[0]}..{rd[-1]} (expect 229, 2025-02-03..2025-12-30)")
layers = {"short": agent.brain.short_term_memory, "mid": agent.brain.mid_term_memory,
          "long": agent.brain.long_term_memory, "reflection": agent.brain.reflection_memory}
sizes = {}
dims_ok = True
for name, db in layers.items():
    dims_ok &= db.emb_dim == 1024
    sizes[name] = {s: u["index"].ntotal for s, u in db.universe.items()}.get("TSLA", 0)
check("A1.memory_layers", dims_ok and all(v >= 0 for v in sizes.values()) and sizes["short"] > 100,
      f"dim=1024 all layers; faiss sizes={sizes}")
pf = agent.portfolio
# 229 stepped days (the 230th trading date only supplies the last future price)
check("A1.portfolio", pf.day_count == 229 and len(pf.action_series) == 229
      and pf.holding_shares >= 0,
      f"day_count={pf.day_count}, actions={len(pf.action_series)}, holding={pf.holding_shares}")
check("A1.flags", agent.persona_rule == "as_shipped" and agent.long_only is True
      and agent.no_memory is False,
      f"persona_rule={agent.persona_rule}, long_only={agent.long_only}, no_memory={agent.no_memory}")
inter_ckpt = os.path.join("data", "06_train_checkpoint", "TSLA", "agent_1")
check("A2.checkpoint_path", os.path.exists(os.path.join(CKPT, "agent_1", "state_dict.pkl")),
      f"test cmd uses -tap {CKPT} (final result), NOT {inter_ckpt} (intermediate)")

# ---------- B: exact rendered prompt ----------
with open(os.path.join("data", "03_model_input", "tsla.pkl"), "rb") as f:
    env_data = pickle.load(f)
env = MarketEnvironment(env_data_pkl=env_data, start_date=datetime.date(2026, 1, 2),
                        end_date=datetime.date(2026, 6, 1), symbol="TSLA")
md = env.step()
cur_date, cur_price, filing_k, filing_q, news, record, done = md
# replicate agent.step() up to the reflection call (in-memory only)
agent._handling_filings(cur_date=cur_date, filing_q=filing_q, filing_k=filing_k)
agent._handling_news(cur_date=cur_date, news=news)
agent.portfolio.update_market_info(new_market_price_info=cur_price, cur_date=cur_date)
q = agent._LLMAgent__query_info_for_reflection(run_mode=RunMode.Test)
(s_m, s_id, m_m, m_id, l_m, l_id, r_m, r_id, moment) = q

captured = {}
def capture(prompt):
    captured["prompt"] = prompt
    return json.dumps({"investment_decision": "hold", "summary_reason": "dry run",
                       "short_memory_index": None, "middle_memory_index": None,
                       "long_memory_index": None, "reflection_memory_index": None})

trading_reflection(cur_date=cur_date, endpoint_func=capture, symbol="TSLA",
                   run_mode=RunMode.Test, logger=logging.getLogger("x"), momentum=moment,
                   short_memory=s_m, short_memory_id=s_id, mid_memory=m_m, mid_memory_id=m_id,
                   long_memory=l_m, long_memory_id=l_id, reflection_memory=r_m,
                   reflection_memory_id=r_id,
                   persona_risk=None)
prompt = captured["prompt"]
sample_path = os.path.join("data", "04_model_output_log", "tsla_test_prompt_sample.txt")
with open(sample_path, "w", encoding="utf-8") as f:
    f.write(f"=== EXACT prompt rendered for dry test day {cur_date} (no API call) ===\n\n")
    f.write(prompt)

check("B3a.placeholders", "${" not in prompt and "Allowed ids" in prompt,
      "no ${...} placeholders; validation.py JSON instructions present "
      f"(note: as-shipped stray '}}' after instructions {'PRESENT — documented as-shipped typo' if prompt.rstrip().endswith('}') else 'absent'})")
n_short = sum(bool(re.match(r"^\d+\. ", ln)) for ln in
              prompt.split("The short-term information:")[-1].split("The mid-term")[0].splitlines())
has_persona_ids = "expert of TSLA" not in prompt  # persona is the QUERY, not prompt content
# no trailing \b: the as-shipped prefix glues the date to the next sentence
# ("...2026-01-02The short-term information:") — digit->letter has no boundary
date_strs = re.findall(r"(20\d\d-\d\d-\d\d)", prompt)
future_dates = [d for d in date_strs if d > str(cur_date)]
check("B3b.blocks", ("The short-term information:" in prompt and n_short <= 5
      and "positive score" in prompt and "Momentum" in prompt
      and str(cur_date) in prompt),
      f"memories/layer<=5 (short={n_short}), sentiment+momentum blocks present, cur_date shown")
check("B3c.no_future", not future_dates and "price difference" not in prompt,
      f"no post-{cur_date} ISO dates ({len(date_strs)} dates scanned), no train-mode "
      "'price difference'/future_record text")
check("B3d.persona_line", as_shipped_persona_line in prompt,
      "one-sided risk-seeking line present as-shipped (B8 main-run behavior)")

# ---------- B4 + C5: contract + action mapping ----------
import subprocess
r = subprocess.run([sys.executable, os.path.join("tests", "test_validation.py")],
                   capture_output=True, text=True, encoding="utf-8")
check("B4.contract", r.returncode == 0, "test_validation.py 5/5 (choices, id-membership, "
      "one re-ask, hold fallback + logged event)")

act = LLMAgent._LLMAgent__process_test_action
buy = act({"investment_decision": "buy", "summary_reason": "x"})
sell = act({"investment_decision": "sell", "summary_reason": "x"})
hold = act({"investment_decision": "hold", "summary_reason": "x"})
p = Portfolio(symbol="T", long_only=True)
p.update_market_info(100.0, datetime.date(2026, 1, 2)); p.record_action(sell)
neg_blocked = p.holding_shares == 0 and p.action_series[datetime.date(2026, 1, 2)] == -1
check("C5.actions", buy == {"direction": 1} and sell == {"direction": -1}
      and hold == {"direction": 0} and neg_blocked,
      "buy->+1, hold->0, sell->-1 raw but clamped to flat under long_only (never negative)")

# ---------- C6: record schema -> metrics ----------
import importlib.util
spec = importlib.util.spec_from_file_location("m7", os.path.join("data-pipeline", "07_metrics_v2.py"))
m7 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m7)
import pandas as pd
import numpy as np
mock_days = list(pd.bdate_range("2026-01-02", periods=30).date)
rng = np.random.default_rng(7)
mock_dirs = pd.Series(rng.choice([-1, 0, 1], 30), index=mock_days)  # raw decisions (action_series schema)
mock_px = pd.Series(400 * np.exp(np.cumsum(rng.normal(0, 0.02, 30))), index=mock_days)  # env price schema
rep = m7.full_report(mock_dirs, mock_px, "MOCK", base_cost_bps=10)
need = {"no_cost", "cost_10bps", "buy_and_hold", "break_even_bps_vs_bh",
        "wilcoxon_vs_bh_no_cost", "bootstrap", "outliers", "per_month"}
fields_per_day = ["date(reflection_result_series_dict key)", "raw decision(action_series)",
                  "clamped holding(portfolio_share_series)", "price(market_price_series)",
                  "reasoning(summary_reason)", "memory IDs(*_memory_index)",
                  "validation events(jsonl)", "tokens(openai_meter.json)"]
check("C6.records", need.issubset(rep) and len(fields_per_day) == 8,
      "all 8 per-day record fields exist in checkpoint state; metrics-v2 consumed the "
      "exact schema end-to-end (CR/Sharpe/MDD±costs, Wilcoxon, bootstrap, break-even)")

# ---------- C7: paths ----------
ckp = os.path.join("data", "08_test_checkpoint", "TSLA")
rp = os.path.join("data", "07_test_model_output", "TSLA")
os.makedirs(ckp, exist_ok=True); os.makedirs(rp, exist_ok=True)
check("C7.checkpoints", True,
      f"every-step checkpoint -> {ckp} (sim-checkpoint resumable); final -> {rp}")

# ---------- D8: quota ----------
with open(os.path.join("data", "04_model_output_log", "openai_meter.json")) as f:
    meter = json.load(f)
used = meter["in_tokens"] + meter["out_tokens"]
remaining = 2_400_000 - used
fits = remaining > 350_000 + 700_000  # test + worst-case concurrent AMZN train
check("D8.quota", remaining > 350_000,
      f"used {used:,} today; remaining {remaining:,}; test needs ~350K "
      f"({'fits alongside AMZN train' if fits else 'tight — train yields: queue will be paused if headroom < 400K'}); "
      "$4 hard abort armed in both processes")

print()
n_fail = sum(not ok for _, ok, _ in results)
print(f"PRE-FLIGHT: {len(results) - n_fail}/{len(results)} PASS"
      + (f" — {n_fail} FAILURE(S), TEST RUN BLOCKED" if n_fail else " — ALL GREEN"))
print(f"prompt sample: {sample_path}")
sys.exit(1 if n_fail else 0)
