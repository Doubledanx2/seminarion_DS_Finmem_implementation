"""Offline test of the A1 validation contract (no API calls): mocked endpoints
exercise trading_reflection end-to-end — valid output, re-ask recovery, and
persistent-failure fallback (test->hold, train->error record)."""
import os
import sys
import json
import logging
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
# isolate synthetic events from the production guardrail-failure log
import tempfile
os.environ["VALIDATION_EVENTS_PATH"] = os.path.join(tempfile.gettempdir(), "validation_events_test.jsonl")
if os.path.exists(os.environ["VALIDATION_EVENTS_PATH"]):
    os.remove(os.environ["VALIDATION_EVENTS_PATH"])

from puppy.reflection import trading_reflection          # noqa: E402  (also proves puppy imports w/o guardrails)
from puppy.run_type import RunMode                       # noqa: E402
from puppy import validation                             # noqa: E402

logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger("t")
kw = dict(
    cur_date=datetime.date(2026, 1, 5), symbol="TSLA", logger=logger, momentum=1,
    short_memory=["good news A", "bad news B"], short_memory_id=[3, 4],
    mid_memory=["10-Q says X"], mid_memory_id=[7],
    long_memory=None, long_memory_id=None,
    reflection_memory=None, reflection_memory_id=None,
)

# 1. valid first try
good = json.dumps({
    "investment_decision": "buy", "summary_reason": "strong delivery numbers",
    "short_memory_index": [{"memory_index": 3}], "middle_memory_index": [{"memory_index": 7}],
    "long_memory_index": [{"memory_index": -1}], "reflection_memory_index": None,
})
r = trading_reflection(endpoint_func=lambda p: good, run_mode=RunMode.Test, **kw)
assert r["investment_decision"] == "buy" and r["short_memory_index"][0]["memory_index"] == 3
assert "long_memory_index" not in r, "placeholder -1 layer should be dropped"
print("1. valid output: ok ->", {k: v for k, v in r.items() if k != 'summary_reason'})

# 2. invalid id then corrected on re-ask (and the re-ask prompt carries the error)
calls = []
def flaky(prompt):
    calls.append(prompt)
    if len(calls) == 1:
        return json.dumps({"investment_decision": "buy", "summary_reason": "x",
                           "short_memory_index": [{"memory_index": 99}]})
    return good
r = trading_reflection(endpoint_func=flaky, run_mode=RunMode.Test, **kw)
assert len(calls) == 2 and "99" in calls[1] and "failed validation" in calls[1]
assert r["investment_decision"] == "buy"
print("2. re-ask recovery: ok (error fed back to model)")

# 3. persistent garbage -> test fallback = hold
r = trading_reflection(endpoint_func=lambda p: "I think you should buy!", run_mode=RunMode.Test, **kw)
assert r["investment_decision"] == "hold" and "summary_reason" in r
print("3. test fallback: ok -> hold")

# 4. persistent garbage in train -> error record, no decision key
kw_train = dict(kw, future_record=2.5)
del kw_train["momentum"]
r = trading_reflection(endpoint_func=lambda p: "not json", run_mode=RunMode.Train, **kw_train)
assert "investment_decision" not in r and "validation failed" in r["summary_reason"]
print("4. train fallback: ok -> error record")

stats = validation.validation_stats()
assert stats["fallbacks"] >= 2 and stats["reasks"] >= 1
print(f"5. failure-rate meter: ok -> {stats}")
print("\nA1 VALIDATION CONTRACT OK")
