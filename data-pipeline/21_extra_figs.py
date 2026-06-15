"""Stage-12 extra figures (user request):
1. bars_sharpe.png — Sharpe bars with the 4th LC-Trader series.
2. finmem_ours_vs_bh_by_ticker.png — FinMem-Ours per-ticker cumulative-return lines
   (solid) with each ticker's Buy & Hold overlaid (dashed, same colour).
Canonical series via 16. No API.
"""
import os
import sys
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
TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
TCOL = {"TSLA": "#E15759", "NFLX": "#1B2A6B", "AMZN": "#17BECF", "MSFT": "#2E78D2", "COIN": "#E8A317"}
SCOL = {"Ours": "#0072B2", "No-mem": "#D55E00", "LC-Trader": "#CC79A7", "B&H": "#009E73"}
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "figure.facecolor": "white",
                     "axes.facecolor": "white", "font.size": 10})

df = pd.read_csv("data/09_results/metrics_canonical.csv")

# ---------- 1. Sharpe bars, 4 series ----------
fig, ax = plt.subplots(figsize=(9, 4.5))
x = np.arange(len(TICKERS)); w = 0.2
for i, (strat, lab) in enumerate([("FinMem-Ours", "Ours"), ("No-memory", "No-mem"),
                                  ("LC-Trader", "LC-Trader"), ("BuyHold", "B&H")]):
    key = {"Ours": "Ours", "No-mem": "No-mem", "LC-Trader": "LC-Trader", "B&H": "B&H"}[lab]
    vals = [df[(df.ticker == t) & (df.strategy == strat)]["sharpe_0"].values for t in TICKERS]
    vals = [v[0] if len(v) else np.nan for v in vals]
    ax.bar(x + (i - 1.5) * w, vals, w, label=lab, color=SCOL[key])
ax.set_xticks(x); ax.set_xticklabels(TICKERS); ax.axhline(0, color="black", lw=0.8)
ax.set_title("Sharpe ratio @0bps — FinMem-Ours vs No-memory vs LC-Trader vs Buy&Hold")
ax.set_ylabel("Sharpe"); ax.legend(ncol=4)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "bars_sharpe.png"), bbox_inches="tight"); plt.close(fig)
print("wrote bars_sharpe.png (4 series incl. LC-Trader)")

# ---------- 2. FinMem-Ours per-ticker cum return + B&H ----------
fig, ax = plt.subplots(figsize=(10, 5.5))
ours_cr, bh_cr = {}, {}
for t in TICKERS:
    r_o = C.series_for(f"{t}_ours", t)[0]
    eq_o = ((1 + r_o).cumprod() - 1) * 100
    r_b = C.bh_returns(t)
    eq_b = ((1 + r_b).cumprod() - 1) * 100
    ax.plot(eq_o.index, eq_o.values, color=TCOL[t], lw=2.2, solid_capstyle="round")
    ax.plot(eq_b.index, eq_b.values, color=TCOL[t], lw=1.3, ls=(0, (4, 2)), alpha=0.55)
    ours_cr[t] = eq_o.iloc[-1]; bh_cr[t] = eq_b.iloc[-1]
ax.axhline(0, color="grey", lw=0.8, ls=":")
ax.grid(True, alpha=0.25)
ax.set_title("FinMem-Ours vs Buy & Hold — cumulative return by ticker (test window, 0 bps)",
             fontsize=13, fontweight="bold", color="#1B2A6B", pad=12)
ax.set_ylabel("Cumulative return (%)"); ax.set_xlabel("")
from matplotlib.lines import Line2D
handles = [Line2D([0], [0], color=TCOL[t], lw=2.4,
                  label=f"{t}   Ours {ours_cr[t]:+.1f}%  ·  B&H {bh_cr[t]:+.1f}%") for t in TICKERS]
handles += [Line2D([0], [0], color="grey", lw=2.2, label="— solid = FinMem-Ours"),
            Line2D([0], [0], color="grey", lw=1.3, ls=(0, (4, 2)), label="-- dashed = Buy & Hold")]
ax.legend(handles=handles, loc="lower left", fontsize=9, framealpha=0.9)
omean = np.mean(list(ours_cr.values())); bmean = np.mean(list(bh_cr.values()))
ax.text(0.99, 0.03, f"mean: Ours {omean:+.1f}%   B&H {bmean:+.1f}%",
        transform=ax.transAxes, ha="right", va="bottom", color="grey", fontsize=10)
fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(os.path.join(FIG, "finmem_ours_vs_bh_by_ticker.png"), bbox_inches="tight"); plt.close(fig)
print("wrote finmem_ours_vs_bh_by_ticker.png (Ours solid + B&H dashed per ticker)")
