"""Stage-11 Part C: render presentation figures as PNG (matplotlib headless, no API).
All numbers via the canonical engine (16). Output: data/09_results/figures/.
"""
import os
import sys
import pickle
import importlib.util

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.getcwd())
spec = importlib.util.spec_from_file_location("c16", os.path.join("data-pipeline", "16_canonical_metrics.py"))
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)

FIG = "data/09_results/figures"
os.makedirs(FIG, exist_ok=True)
TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
# colorblind-safe (Okabe-Ito)
COL = {"Ours": "#0072B2", "No-mem": "#D55E00", "B&H": "#009E73",
       "seeking": "#E69F00", "averse": "#56B4E9",
       "short": "#0072B2", "mid": "#009E73", "long": "#D55E00", "reflection": "#CC79A7"}
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "figure.facecolor": "white",
                     "axes.facecolor": "white", "font.size": 10})


def eq_curve(r):
    return (1 + r).cumprod()


def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(FIG, name), bbox_inches="tight"); plt.close(fig)
    print("wrote", name)


# 1. equity curves per ticker
for t in TICKERS:
    fig, ax = plt.subplots(figsize=(7, 4))
    r_o = C.series_for(f"{t}_ours", t)[0]
    ax.plot(eq_curve(r_o).index, eq_curve(r_o).values, color=COL["Ours"], lw=2, label="FinMem-Ours")
    nmtag = f"{t}_ours_nomem"
    if os.path.exists(f"data/07_test_model_output/{nmtag}/agent_1/state_dict.pkl"):
        r_n = C.series_for(nmtag, t)[0]
        ax.plot(eq_curve(r_n).index, eq_curve(r_n).values, color=COL["No-mem"], lw=2, ls="--", label="No-memory")
    r_b = C.bh_returns(t)
    ax.plot(eq_curve(r_b).index, eq_curve(r_b).values, color=COL["B&H"], lw=2, ls=":", label="Buy & Hold")
    ax.axhline(1.0, color="grey", lw=0.7)
    ax.set_title(f"{t} — equity curve (test 2026 H1, canonical)"); ax.set_xlabel("date")
    ax.set_ylabel("growth of $1"); ax.legend(); fig.autofmt_xdate()
    save(fig, f"equity_{t}.png")

# 2 & 3. grouped bars: cum return and Sharpe
df = pd.read_csv("data/09_results/metrics_canonical.csv")
for metric, fname, title, pct in [("cr_0", "bars_cum_return.png", "Cumulative return @0bps", True),
                                   ("sharpe_0", "bars_sharpe.png", "Sharpe @0bps", False)]:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(TICKERS)); w = 0.27
    for i, (strat, lab, c) in enumerate([("FinMem-Ours", "Ours", COL["Ours"]),
                                         ("No-memory", "No-mem", COL["No-mem"]),
                                         ("BuyHold", "B&H", COL["B&H"])]):
        vals = [df[(df.ticker == t) & (df.strategy == strat)][metric].values for t in TICKERS]
        vals = [v[0] * (100 if pct else 1) if len(v) else np.nan for v in vals]
        ax.bar(x + (i - 1) * w, vals, w, label=lab, color=c)
    ax.set_xticks(x); ax.set_xticklabels(TICKERS); ax.axhline(0, color="black", lw=0.8)
    ax.set_title(title + " — FinMem-Ours vs No-memory vs Buy&Hold")
    ax.set_ylabel("%" if pct else "Sharpe"); ax.legend()
    save(fig, fname)

# 4. cost / break-even per ticker
for t in TICKERS:
    fig, ax = plt.subplots(figsize=(6.5, 4))
    bpsg = np.arange(0, 51, 2)
    px = C.env_prices(t); pos = C.carry_position(C.decisions(f"{t}_ours"))
    crs = [float(np.prod(1 + C.daily_returns(pos, px, b)) - 1) * 100 for b in bpsg]
    bh = float(np.prod(1 + C.bh_returns(t)) - 1) * 100
    ax.plot(bpsg, crs, color=COL["Ours"], lw=2, label="FinMem-Ours CR")
    ax.axhline(bh, color=COL["B&H"], ls=":", lw=2, label=f"Buy & Hold ({bh:+.1f}%)")
    below = [b for b, c in zip(bpsg, crs) if c < bh]
    if below:
        be = below[0]
        ax.plot([be], [bh], "o", color="#D55E00", ms=8, label=f"break-even ≈ {be} bps")
    ax.set_title(f"{t} — return vs transaction cost"); ax.set_xlabel("cost (bps/trade)")
    ax.set_ylabel("cumulative return %"); ax.legend()
    save(fig, f"costs_breakeven_{t}.png")

# 5. persona timeline NFLX (mode bands + price)
t = "NFLX"
px = C.env_prices(t); dec = C.decisions(f"{t}_ours")
days = list(px.index); pl = px.values
modes = []
for i, d in enumerate(days):
    modes.append("seeking" if i < 3 else ("averse" if (pl[i] - pl[i - 3]) < 0 else "seeking"))
fig, ax = plt.subplots(figsize=(9, 4))
for i in range(len(days) - 1):
    ax.axvspan(days[i], days[i + 1], color=COL[modes[i]], alpha=0.35, lw=0)
ax.plot(days, pl, color="black", lw=1.6)
ax.set_title("NFLX — adaptive persona mode (orange=risk-seeking, blue=risk-averse) + price")
ax.set_xlabel("date"); ax.set_ylabel("NFLX price")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=COL["seeking"], label="risk-seeking", alpha=.5),
                   Patch(color=COL["averse"], label="risk-averse", alpha=.5)], loc="upper left")
fig.autofmt_xdate(); save(fig, "persona_timeline_NFLX.png")

# 6. citation share per ticker (stacked)
LAYER_DIRS = {"short": "short_term_memory", "mid": "mid_term_memory",
              "long": "long_term_memory", "reflection": "reflection_memory"}
CITE = [("short_memory_index", "short"), ("middle_memory_index", "mid"),
        ("long_memory_index", "long"), ("reflection_memory_index", "reflection")]
share = {}
for t in TICKERS:
    sd = pickle.load(open(f"data/07_test_model_output/{t}_ours/agent_1/state_dict.pkl", "rb"))
    cnt = {"short": 0, "mid": 0, "long": 0, "reflection": 0}
    for d, r in sd["reflection_result_series_dict"].items():
        if d.year != 2026:
            continue
        for fld, ln in CITE:
            for it in (r.get(fld) or []):
                mid = it.get("memory_index") if isinstance(it, dict) else it
                if mid not in (None, -1):
                    cnt[ln] += 1
    tot = sum(cnt.values()) or 1
    share[t] = {k: v / tot for k, v in cnt.items()}
fig, ax = plt.subplots(figsize=(8, 4.5))
bottom = np.zeros(len(TICKERS))
for ln in ["short", "mid", "long", "reflection"]:
    vals = [share[t][ln] * 100 for t in TICKERS]
    ax.bar(TICKERS, vals, bottom=bottom, label=ln, color=COL[ln]); bottom += vals
ax.set_title("Memory-layer citation share per ticker (FinMem-Ours)")
ax.set_ylabel("% of citations"); ax.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.22))
save(fig, "citation_share.png")

# 7. vector-DB PCA scatter (NFLX, TSLA)
from sklearn.decomposition import PCA
import faiss
for t in ["NFLX", "TSLA"]:
    base = f"data/07_test_model_output/{t}_ours/agent_1/brain"
    vecs, layers, imps = [], [], []
    for ln, ld in LAYER_DIRS.items():
        ip = os.path.join(base, ld, f"{t}.index")
        up = os.path.join(base, ld, "universe_index.pkl")
        if not (os.path.exists(ip) and os.path.exists(up)):
            continue
        idx = faiss.read_index(ip)
        uni = pickle.load(open(up, "rb"))
        recs = uni.get(t, {}).get("score_memory", [])
        for m in recs:  # reconstruct each vector by its real memory id (IndexIDMap2)
            try:
                v = idx.reconstruct(int(m["id"]))
            except RuntimeError:
                continue
            vecs.append(v.reshape(1, -1)); layers.append(ln); imps.append(m["important_score"])
    if not vecs:
        continue
    X = np.vstack(vecs)
    P = PCA(n_components=2, random_state=0).fit_transform(X)
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    imps = np.array(imps, dtype=float)
    for ln in ["short", "mid", "long", "reflection"]:
        m = np.array([l == ln for l in layers])
        if m.sum():
            ax.scatter(P[m, 0], P[m, 1], s=8 + (imps[m] - imps.min()) / max(1, np.ptp(imps)) * 60,
                       c=COL[ln], alpha=0.6, label=ln, edgecolors="none")
    ax.set_title(f"{t} — end-state memory vectors (ada-002, PCA 2-D; size∝importance)")
    ax.set_xlabel("PC1"); ax.set_ylabel("PC2"); ax.legend()
    save(fig, f"vectordb_{t}.png")

# 8. memory growth: NFLX-Ours deep occupancy vs TSLA as-shipped revolving door
def long_occ(events_path, symbol):
    if not os.path.exists(events_path):
        return None
    import json
    alive, series = set(), []
    cur = None
    seq = 0
    rows = [json.loads(l) for l in open(events_path, encoding="utf-8-sig")]
    for ev in rows:
        seq += 1
        if ev.get("layer") in ("agent_1_long", "long_term_memory") or ev.get("layer", "").endswith("long"):
            if ev["event"] in ("jump_in_up", "ingest"):
                alive.add(ev["id"])
            elif ev["event"] in ("demote_out", "purge"):
                alive.discard(ev["id"])
        series.append(len(alive))
    return series

fig, ax = plt.subplots(figsize=(8, 4))
nf = long_occ("data/04_model_output_log/memory_events_NFLX_ours_train.jsonl", "NFLX")
if nf:
    ax.plot(np.linspace(0, 1, len(nf)), nf, color=COL["Ours"], lw=2,
            label="FinMem-Ours NFLX deep layer (retains)")
# as-shipped TSLA: reconstruct from run-log replay summary (F2: capped ~7, avg 3-day)
ax.axhline(7, color=COL["No-mem"], ls="--", lw=2, label="as-shipped TSLA deep layer (≤7, 3-day revolving — F2)")
ax.set_title("Deep-layer occupancy: FinMem-Ours retention vs as-shipped revolving door")
ax.set_xlabel("training progress (fraction)"); ax.set_ylabel("# items in deep layer"); ax.legend()
save(fig, "memory_growth_NFLX.png")

print("\nFIGURES DONE ->", FIG)
print(sorted(os.listdir(FIG)))
