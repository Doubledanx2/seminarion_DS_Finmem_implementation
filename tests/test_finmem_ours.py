"""Offline behavioral tests for the FinMem-Ours configuration (no API calls)."""
import os
import sys
import json
import logging
import datetime
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ["VALIDATION_EVENTS_PATH"] = os.path.join(tempfile.gettempdir(), "ours_ev.jsonl")
logging.disable(logging.CRITICAL)

from puppy.portfolio import Portfolio                       # noqa: E402
from puppy.reflection import trading_reflection             # noqa: E402
from puppy.run_type import RunMode                          # noqa: E402

logger = logging.getLogger("t")
d0 = datetime.date(2026, 1, 2)

# 1. unit position {0,+1}: buy stacks to 1 max; sell exits to 0; never negative
p = Portfolio(symbol="T", long_only=True, unit_position=True)
for i, (direction, expect) in enumerate([(1, 1), (1, 1), (-1, 0), (-1, 0), (1, 1), (0, 1)]):
    p.update_market_info(100.0 + i, d0 + datetime.timedelta(days=i))
    p.record_action({"direction": direction})
    assert p.holding_shares == expect, (i, direction, p.holding_shares)
assert list(p.action_series.values()) == [1, 1, -1, -1, 1, 0], "raw decisions preserved"
print("1. unit position {0,+1} ok (cap at 1, exit to 0, raw decisions intact)")

# 2. persona switch window=3 (paper §3.1): 3-day PnL sign, independent of M=7
p2 = Portfolio(symbol="T", lookback_window_size=7, long_only=True)
prices = [100, 103, 106, 109, 112, 111.9, 111.8, 111.7]  # strong early gains, tiny 3-day dip
for i, px in enumerate(prices):
    p2.update_market_info(float(px), d0 + datetime.timedelta(days=i))
    p2.record_action({"direction": 1})
    p2.update_portfolio_series()
assert p2.get_lookback_risk_state(window=3) == "averse"
assert p2.get_lookback_risk_state(window=7) == "seeking"  # 7-day still positive
print("2. persona window=3 ok (3d averse while 7d seeking on same series)")

# 3. memorydb: downward jumps disabled + pure-age recency (no reset on promotion)
from puppy.memorydb import MemoryDB, id_generator_func
from puppy.memory_functions import (
    get_importance_score_initialization_func, R_ConstantInitialization,
    LinearCompoundScore, ExponentialDecay, LinearImportanceScoreChange)


class FakeEmb:
    def __call__(self, texts):
        import numpy as np
        if isinstance(texts, str):
            texts = [texts]
        rng = np.random.default_rng(abs(hash(tuple(texts))) % (2**31))
        return rng.normal(size=(len(texts), 8)).astype("float32")

    def get_embedding_dimension(self):
        return 8


import puppy.memorydb as mdb
_orig = mdb.make_embedding_function
mdb.make_embedding_function = lambda **kw: FakeEmb()
try:
    def mk(upper, lower, factor):
        m = MemoryDB(db_name="t", id_generator=id_generator_func(),
                     jump_threshold_upper=upper, jump_threshold_lower=lower,
                     logger=logger, emb_config={},
                     importance_score_initialization=get_importance_score_initialization_func("sample", "long"),
                     recency_score_initialization=R_ConstantInitialization(),
                     compound_score_calculation=LinearCompoundScore(),
                     importance_score_change_access_counter=LinearImportanceScoreChange(),
                     decay_function=ExponentialDecay(recency_factor=365, importance_factor=factor),
                     clean_up_threshold_dict={"recency_threshold": 0.05, "importance_threshold": 5})
        return m

    long_db = mk(999999999, 80, 0.988)
    long_db.add_memory("T", d0, ["a deep memory"])
    rec = long_db.universe["T"]["score_memory"][0]
    rec["important_score"] = 79.0  # below the exit bar

    long_db.disable_downward_jumps = False
    up, down, _ = long_db.prepare_jump()
    assert "T" in down, "as-shipped: item below 80 must be collected for demotion"
    long_db.accept_jump((up, down), "down")  # put it back for the next check

    long_db.disable_downward_jumps = True
    up, down, _ = long_db.prepare_jump()
    assert "T" not in down and len(long_db.universe["T"]["score_memory"]) == 1, \
        "FinMem-Ours: item below 80 must STAY in long"
    print("3. downward jumps disabled ok (deep retention)")

    # pure-age recency: promotion must NOT reset recency/delta
    mid_db = mk(80, 60, 0.967)
    mid_db.reset_recency_on_promotion = False
    obj = {"text": "x", "id": 999, "important_score": 85.0, "recency_score": 0.4,
           "delta": 25, "important_score_recency_compound_score": 1.25,
           "access_counter": 0, "date": d0}
    import numpy as np
    mid_db.accept_jump(({"T": {"jump_object_list": [obj],
                               "emb_list": np.ones((1, 8), dtype="float32")}}, {}), "up")
    rec2 = mid_db.universe["T"]["score_memory"][0]
    assert rec2["delta"] == 25 and rec2["recency_score"] == 0.4, "no reset under pure age"
    mid_db.reset_recency_on_promotion = True
    obj2 = dict(obj, id=1000)
    mid_db.accept_jump(({"T": {"jump_object_list": [obj2],
                               "emb_list": np.ones((1, 8), dtype="float32")}}, {}), "up")
    rec3 = next(r for r in mid_db.universe["T"]["score_memory"] if r["id"] == 1000)
    assert rec3["delta"] == 0 and rec3["recency_score"] == 1.0, "as-shipped reset intact"
    print("4. pure-age recency ok (no reset on promotion; as-shipped path intact)")
finally:
    mdb.make_embedding_function = _orig

# 5. observation window text: M=7 cumulative return in the test prompt
captured = {}
def cap(prompt):
    captured["p"] = prompt
    return json.dumps({"investment_decision": "hold", "summary_reason": "x"})
kw = dict(cur_date=d0, symbol="TSLA", logger=logger,
          short_memory=["m"], short_memory_id=[1], mid_memory=None, mid_memory_id=None,
          long_memory=None, long_memory_id=None, reflection_memory=None, reflection_memory_id=None)
trading_reflection(endpoint_func=cap, run_mode=RunMode.Test, momentum=1, momentum_window=7, **kw)
assert "past 7 days" in captured["p"] and "past 3 days" not in captured["p"]
trading_reflection(endpoint_func=cap, run_mode=RunMode.Test, momentum=1, **kw)
assert "past 3 days" in captured["p"], "as-shipped default unchanged"
print("5. observation window ok (7-day text for Ours, 3-day default intact)")

# 6. filing seeding: true filedAt stamped, 10-K->long, 10-Q->mid
class SeedBrain:
    def __init__(self):
        self.calls = []

    def add_memory_long(self, symbol, date, text):
        self.calls.append(("long", date))

    def add_memory_mid(self, symbol, date, text):
        self.calls.append(("mid", date))


class SeedAgent:
    from puppy.agent import LLMAgent
    seed_filings = LLMAgent.seed_filings
    trading_symbol = "TSLA"
    logger = logger
    brain = SeedBrain()


seedfile = os.path.join(tempfile.gettempdir(), "seeds.json")
json.dump([{"symbol": "TSLA", "type": "10-K", "date": "2025-01-30", "summary": "s"},
           {"symbol": "MSFT", "type": "10-Q", "date": "2025-01-29", "summary": "s"}],
          open(seedfile, "w"))
a = SeedAgent()
n = a.seed_filings(seedfile)
assert n == 1 and a.brain.calls == [("long", datetime.date(2025, 1, 30))], a.brain.calls
print("6. filing seeding ok (own-symbol only, true filedAt, 10-K->long)")

print("\nFINMEM-OURS BEHAVIORS OK")
