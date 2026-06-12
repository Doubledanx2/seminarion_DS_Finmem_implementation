"""Stage-8 step 8: portfolio layer over the 5 completed FinMem-Ours test runs.
One gpt-4.1-mini call per test day (~104). Reads decisions straight from the test
agents' state_dicts; writes weights+reasoning jsonl and a result json with the
portfolio equity curve vs equal-weight buy&hold. Idempotent: skips if result exists.
"""
import os
import sys
import json
import pickle
import logging
import datetime

import numpy as np

sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv

load_dotenv()
from puppy.chat import ChatOpenAICompatible           # noqa: E402
from puppy.portfolio_layer import PortfolioAllocator  # noqa: E402

TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
OUT = os.path.join("data", "09_results")
RESULT = os.path.join(OUT, "portfolio_layer_result.json")

if os.path.exists(RESULT):
    print(f"already done -> {RESULT}")
    sys.exit(0)

# decisions + reasons per ticker per test day
decisions, prices = {}, {}
for t in TICKERS:
    sd = pickle.load(open(os.path.join("data", "07_test_model_output", f"{t}_ours",
                                       "agent_1", "state_dict.pkl"), "rb"))
    refl = sd["reflection_result_series_dict"]
    decisions[t] = {d: {"decision": r.get("investment_decision", "hold"),
                        "reason": str(r.get("summary_reason", ""))[:300]}
                    for d, r in refl.items() if d.year == 2026}
    pf = sd["portfolio"]
    prices[t] = dict(zip(pf.date_series, pf.market_price_series))

days = sorted(set.intersection(*(set(decisions[t]) for t in TICKERS)))
print(f"portfolio layer over {len(days)} common test days")

chat = ChatOpenAICompatible(
    end_point="https://api.openai.com/v1/chat/completions", model="gpt-4.1-mini",
    system_message="You are a helpful assistant.",
    other_parameters={"temperature": 1.0, "daily_token_budget": 2_400_000,
                      "wait_for_reset": False, "paid_overflow": True, "paid_cap_usd": 3.00})
alloc = PortfolioAllocator(endpoint_func=chat.guardrail_endpoint(),
                           logger=logging.getLogger("portfolio"))

weights_series = {}
for d in days:
    weights_series[str(d)] = alloc.allocate(d, {t: decisions[t][d] for t in TICKERS})

# evaluate: weights at day t applied to t -> t+1 returns
port_rets, ew_rets = [], []
for i, d in enumerate(days[:-1]):
    nxt = days[i + 1]
    rets = {t: prices[t][nxt] / prices[t][d] - 1 for t in TICKERS
            if d in prices[t] and nxt in prices[t]}
    w = weights_series[str(d)]
    port_rets.append(sum(w.get(t, 0) * rets.get(t, 0) for t in TICKERS))
    ew_rets.append(np.mean([rets.get(t, 0) for t in TICKERS]))

os.makedirs(OUT, exist_ok=True)
result = {
    "days": [str(d) for d in days],
    "weights": weights_series,
    "portfolio_cum_return": float(np.prod([1 + r for r in port_rets]) - 1),
    "equal_weight_bh_cum_return": float(np.prod([1 + r for r in ew_rets]) - 1),
    "portfolio_daily": port_rets,
    "equal_weight_daily": ew_rets,
}
with open(RESULT, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=1)
print(f"portfolio CR {result['portfolio_cum_return']*100:+.1f}% vs EW-B&H "
      f"{result['equal_weight_bh_cum_return']*100:+.1f}% -> {RESULT}")
