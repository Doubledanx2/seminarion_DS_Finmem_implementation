"""Offline behavioral checks for addendum A3.2/A4 items (no API calls)."""
import os
import sys
import json
import logging
import datetime
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from puppy.portfolio import Portfolio                 # noqa: E402
from puppy.reflection import trading_reflection       # noqa: E402
from puppy.run_type import RunMode                    # noqa: E402
from puppy.chat import TokenMeter, BudgetExhausted    # noqa: E402
from puppy.agent import TextTruncator                 # noqa: E402
from puppy.prompts import persona_averse, as_shipped_persona_line  # noqa: E402

logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger("t")

# 1. Sin 7 long-only clamp: Sell at flat never opens a short; raw decisions kept
p = Portfolio(symbol="TSLA", lookback_window_size=7, long_only=True)
p.update_market_info(100.0, datetime.date(2026, 1, 2))
p.record_action({"direction": -1})
assert p.holding_shares == 0, "long-only must clamp at 0"
p.update_market_info(101.0, datetime.date(2026, 1, 3))
p.record_action({"direction": 1})
assert p.holding_shares == 1
assert list(p.action_series.values()) == [-1, 1], "raw decisions must be preserved"
p2 = Portfolio(symbol="TSLA", long_only=False)
p2.update_market_info(100.0, datetime.date(2026, 1, 2))
p2.record_action({"direction": -1})
assert p2.holding_shares == -1, "long-short path must stay paper-faithful"
print("1. long-only clamp ok (raw decisions preserved; long-short path intact)")

# 2. B8 risk state: losing lookback PnL -> averse
p3 = Portfolio(symbol="TSLA", lookback_window_size=3, long_only=False)
for i, price in enumerate([100, 99, 97, 94, 90]):
    p3.update_market_info(float(price), datetime.date(2026, 1, 2) + datetime.timedelta(days=i))
    p3.record_action({"direction": 1})  # long while falling -> losses
    p3.update_portfolio_series()
assert p3.get_lookback_risk_state() == "averse", p3.get_lookback_risk_state()
print("2. B8 risk state ok (losing lookback -> averse)")

# 3. B8 prompt swap: persona_risk='averse' replaces the as-shipped line
captured = {}
def capture(prompt):
    captured["p"] = prompt
    return json.dumps({"investment_decision": "hold", "summary_reason": "x"})
kw = dict(cur_date=datetime.date(2026, 1, 5), symbol="TSLA", logger=logger, momentum=1,
          short_memory=["a"], short_memory_id=[1], mid_memory=None, mid_memory_id=None,
          long_memory=None, long_memory_id=None, reflection_memory=None, reflection_memory_id=None)
trading_reflection(endpoint_func=capture, run_mode=RunMode.Test, persona_risk="averse", **kw)
assert persona_averse in captured["p"] and as_shipped_persona_line not in captured["p"]
trading_reflection(endpoint_func=capture, run_mode=RunMode.Test, persona_risk=None, **kw)
assert as_shipped_persona_line in captured["p"], "as-shipped prompt must be unchanged"
print("3. B8 prompt swap ok (paper_rule injects averse line; as-shipped untouched)")

# 4. A3.2 hard abort at $4 projected + daily-overflow guard
tmp = os.path.join(tempfile.gettempdir(), "meter_a3.json")
if os.path.exists(tmp):
    os.remove(tmp)
m = TokenMeter(path=tmp, daily_token_budget=None)
m.add("gpt-4.1-mini", {"prompt_tokens": 9_000_000, "completion_tokens": 300_000})  # ~ $4.08
try:
    m.check_budget("gpt-4.1-mini")
    raise AssertionError("should have aborted at $4 projected")
except BudgetExhausted as e:
    print(f"4. $4 hard abort ok ({e})")
m2 = TokenMeter(path=tmp + "2", daily_token_budget=100_000, wait_for_reset=False)
m2.add("gpt-4.1-mini", {"prompt_tokens": 80_000, "completion_tokens": 5_000})
try:
    m2.check_budget("gpt-4.1-mini")  # 85K + 16K headroom > 100K -> must refuse
    raise AssertionError("should refuse a request that could overflow the daily quota")
except Exception as e:
    print(f"5. daily-overflow guard ok ({type(e).__name__})")

# 5. A4.6 tiktoken truncator for gpt-4.1-mini
tt = TextTruncator("gpt-4.1-mini")
lst, total = tt.process_list_of_texts(["hello world " * 200, "second text"], max_total_tokens=50)
assert total <= 50 and len(lst) >= 1
txt, n = tt.truncate_text("hello world " * 200, max_tokens=10)
assert n == 10
print("6. tiktoken truncator ok (list + single-text truncation at token budget)")

print("\nA3.2/A4 BEHAVIORS OK")
