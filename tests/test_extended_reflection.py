"""Offline test of the V-E extended-reflection module (mocked LLM, no API)."""
import os
import sys
import json
import logging
import datetime
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ["VALIDATION_EVENTS_PATH"] = os.path.join(tempfile.gettempdir(), "ve_events.jsonl")

import numpy as np  # noqa: E402
from puppy import extended_reflection  # noqa: E402

logging.disable(logging.CRITICAL)


class FakeBrain:
    def __init__(self):
        self.written = []

    def add_memory_reflection(self, symbol, date, text):
        self.written.append(("reflection", date, text))

    def add_memory_long(self, symbol, date, text):
        self.written.append(("long", date, text))


class FakePortfolio:
    def __init__(self, dates, prices):
        self.date_series = dates
        self.market_price_series = np.array(prices)


class FakeAgent:
    def __init__(self, endpoint):
        self.trading_symbol = "TSLA"
        self.look_back_window_size = 7
        self.logger = logging.getLogger("t")
        self.brain = FakeBrain()
        self.guardrail_endpoint = endpoint
        self.extended_reflection_target = "reflection"
        days = [datetime.date(2026, 1, 2) + datetime.timedelta(days=i) for i in range(10)]
        self.portfolio = FakePortfolio(days, [100 + i for i in range(10)])
        self.reflection_result_series_dict = {
            d: {"investment_decision": "buy", "summary_reason": f"reason {i}"}
            for i, d in enumerate(days[:9])
        }


cur = datetime.date(2026, 1, 12)

# 1. happy path -> insight written to reflection layer
good = json.dumps({"insight": "Buys following 3-day momentum worked; fading strength did not.",
                   "confidence": "med"})
a = FakeAgent(lambda p: good)
out = extended_reflection.step(a, cur)
assert out["confidence"] == "med" and len(a.brain.written) == 1
layer, d, text = a.brain.written[0]
assert layer == "reflection" and "[extended reflection, confidence=med]" in text
print("1. happy path ok -> reflection layer, tagged insight")

# 2. history block: last M=7 days only, includes decisions + realized returns
prompts = []
a2 = FakeAgent(lambda p: (prompts.append(p) or good))
extended_reflection.step(a2, cur)
assert prompts[0].count("decision=buy") == 7, prompts[0]
assert prompts[0].count("realized next-day return=+0.9") >= 5, "realized returns must be present"
print("2. history block ok (exactly M=7 days, returns present)")

# 3. bad JSON then corrected on re-ask
calls = []
def flaky(p):
    calls.append(p)
    return good if len(calls) > 1 else "I think you should journal more."
a3 = FakeAgent(flaky)
out = extended_reflection.step(a3, cur)
assert len(calls) == 2 and "failed validation" in calls[1] and out["confidence"] == "med"
print("3. re-ask ok (error fed back)")

# 4. persistent garbage -> skip day, no memory written
a4 = FakeAgent(lambda p: "nope")
out = extended_reflection.step(a4, cur)
assert out == {} and len(a4.brain.written) == 0
print("4. persistent failure -> day skipped, nothing written")

# 5. target=long honored
a5 = FakeAgent(lambda p: good)
a5.extended_reflection_target = "long"
extended_reflection.step(a5, cur)
assert a5.brain.written[0][0] == "long"
print("5. config target=long ok")

print("\nEXTENDED REFLECTION (V-E) MODULE OK")
