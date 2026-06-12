"""Task 3.2 — OFFLINE deep-layer replay from the verbose run log (no API).

The authors' BrainDB.step() dumps EVERY memory record in EVERY layer EVERY sim day
(post-decay, pre-jump) into <SYMBOL>_run.log. This parser reconstructs:
  - per-day long-layer occupancy,
  - all layer transitions (promote/demote) and disappearances (purge),
  - full life timelines for chosen ids (10-K ingests, Dec-29/30 long items, #3023).

Usage: python data-pipeline/09_deep_layer_trace.py TSLA [id ...]
"""
import os
import re
import sys
from collections import defaultdict

SYMBOL = sys.argv[1].upper() if len(sys.argv) > 1 else "TSLA"
LOG = os.path.join("data", "04_model_output_log", f"{SYMBOL}_run.log")

REC_RE = re.compile(
    r"'id': (\d+), 'important_score': ([0-9.e+-]+), 'recency_score': ([0-9.e+-]+), "
    r"'delta': (\d+), 'important_score_recency_compound_score': [0-9.e+-]+, "
    r"'access_counter': (-?\d+), 'date': datetime\.date\((\d+), (\d+), (\d+)\)\}\s*$"
)
DATE_RE = re.compile(r" - Date (\d{4}-\d{2}-\d{2})")
LAYER_RE = re.compile(r" (short|mid|long|reflection) term memory " + SYMBOL)

# state[id] -> list of (sim_date, layer, importance, recency, delta, access)
timeline = defaultdict(list)
long_occupancy = {}     # sim_date -> [ids]
cur_date = None
cur_layer = None
day_layers = defaultdict(set)   # id -> layer for the current day

with open(LOG, encoding="utf-8", errors="replace") as f:
    for line in f:
        m = DATE_RE.search(line)
        if m:
            cur_date = m.group(1)
            continue
        m = LAYER_RE.search(line)
        if m:
            cur_layer = m.group(1)
            continue
        if cur_date is None or cur_layer is None or "'id':" not in line:
            continue
        m = REC_RE.search(line)
        if not m:
            continue
        mid = int(m.group(1))
        rec = (cur_date, cur_layer, float(m.group(2)), float(m.group(3)),
               int(m.group(4)), int(m.group(5)))
        tl = timeline[mid]
        if not tl or tl[-1][0] != cur_date or tl[-1][1] != cur_layer:
            tl.append(rec)
        if cur_layer == "long":
            long_occupancy.setdefault(cur_date, [])
            if mid not in long_occupancy[cur_date]:
                long_occupancy[cur_date].append(mid)

print(f"parsed {len(timeline)} distinct memory ids over "
      f"{len({r[0] for t in timeline.values() for r in t})} sim days\n")

# ---- long-layer occupancy ----
days = sorted(long_occupancy)
ever_long = sorted({i for ids in long_occupancy.values() for i in ids})
print(f"LONG layer: {len(ever_long)} distinct ids EVER present; "
      f"occupancy min={min((len(v) for v in long_occupancy.values()), default=0)} "
      f"max={max((len(v) for v in long_occupancy.values()), default=0)} "
      f"over {len(days)} days with any occupancy "
      f"(of {len({r[0] for t in timeline.values() for r in t})} total days)")

# ---- transitions ----
promotes, demotes = [], []
for mid, tl in timeline.items():
    for a, b in zip(tl, tl[1:]):
        order = {"short": 0, "mid": 1, "long": 2, "reflection": 0}
        if a[1] != b[1] and {a[1], b[1]} <= {"short", "mid", "long"}:
            (promotes if order[b[1]] > order[a[1]] else demotes).append(
                (mid, a[0], a[1], b[0], b[1], a[2], b[2]))
up_to_long = [p for p in promotes if p[4] == "long"]
down_from_long = [d for d in demotes if d[2] == "long"]
print(f"transitions: {len(promotes)} promotions ({len(up_to_long)} into long), "
      f"{len(demotes)} demotions ({len(down_from_long)} out of long)")
# residence time in long
res = []
for mid, tl in timeline.items():
    in_long = [r[0] for r in tl if r[1] == "long"]
    if in_long:
        seen_days = sorted({r[0] for r in tl})
        idx = {d: i for i, d in enumerate(seen_days)}
        spans = (idx[in_long[-1]] - idx[in_long[0]] + 1)
        res.append((mid, in_long[0], in_long[-1], spans))
if res:
    avg = sum(r[3] for r in res) / len(res)
    print(f"long-layer residence (appearance-span days): avg={avg:.1f}, "
          f"max={max(r[3] for r in res)} — items: {[(r[0], r[1], r[2]) for r in sorted(res)[:12]]}")

# ---- chosen ids ----
targets = [int(x) for x in sys.argv[2:]] or ([3023] + ever_long[:6])
for t in targets:
    tl = timeline.get(t)
    if not tl:
        print(f"\nid {t}: not found in log")
        continue
    print(f"\nid {t} timeline ({len(tl)} layer/day points, first 14 + last 4):")
    for r in tl[:14]:
        print(f"  {r[0]} {r[1]:10s} imp={r[2]:7.2f} rec={r[3]:.4f} delta={r[4]:3d} access={r[5]}")
    if len(tl) > 18:
        print(f"  ... ({len(tl) - 18} more)")
    for r in tl[-4:]:
        print(f"  {r[0]} {r[1]:10s} imp={r[2]:7.2f} rec={r[3]:.4f} delta={r[4]:3d} access={r[5]}")
