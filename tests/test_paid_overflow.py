"""Offline test: Stage-8 paid-overflow TokenMeter (boundary logging, $3 cap)."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from puppy.chat import TokenMeter, BudgetExhausted

tmp = os.path.join(tempfile.gettempdir(), "paid_meter.json")
if os.path.exists(tmp):
    os.remove(tmp)
m = TokenMeter(path=tmp, daily_token_budget=100_000, paid_overflow=True, paid_cap_usd=3.00)

m.add("gpt-4.1-mini", {"prompt_tokens": 80_000, "completion_tokens": 5_000})
assert m.state["paid_in"] == 0, "below pool -> free"
m.check_budget("gpt-4.1-mini")  # must NOT sleep or raise
print("1. free-pool phase ok (no paid tokens, no sleep)")

m.add("gpt-4.1-mini", {"prompt_tokens": 20_000, "completion_tokens": 2_000})  # straddles
assert m.state["paid_in"] == 20_000 and m.state["paid_out"] == 2_000, "straddle counted fully paid"
print("2. boundary straddle ok (whole call paid, switchover logged above)")

m.check_budget("gpt-4.1-mini")  # paid ~ $0.011 < cap
m.add("gpt-4.1-mini", {"prompt_tokens": 7_000_000, "completion_tokens": 100_000})  # ~$2.96 paid
m.add("gpt-4.1-mini", {"prompt_tokens": 200_000, "completion_tokens": 10_000})
try:
    m.check_budget("gpt-4.1-mini")
    raise AssertionError("should abort at $3 paid cap")
except BudgetExhausted as e:
    print(f"3. $3.00 paid cap ok ({e})")
print(f"   paid cost = ${m.paid_cost():.2f}; free-phase tokens never counted")
print("\nPAID OVERFLOW METER OK")
