"""Styled all-tickers chart: FinMem-Ours cumulative return per ticker (solid) WITH
Buy & Hold overlaid (same colour, dashed) — matches finmem_ours_all_tickers.png style.
Canonical series via 16. No API."""
import os
import sys
import importlib.util

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, os.getcwd())
spec = importlib.util.spec_from_file_location("c16", os.path.join("data-pipeline", "16_canonical_metrics.py"))
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)

FIG = "data/09_results/figures"
# colours matched to finmem_ours_all_tickers.png
TCOL = {"AMZN": "#19C3A2", "NFLX": "#16215B", "MSFT": "#2E7FC1", "COIN": "#F0A93B", "TSLA": "#E8625A"}
ORDER = ["AMZN", "NFLX", "MSFT", "COIN", "TSLA"]
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "figure.facecolor": "white",
                     "axes.facecolor": "white", "font.size": 11})

fig, ax = plt.subplots(figsize=(10.5, 5.8))
ours_cr, bh_cr = {}, {}
for t in ORDER:
    r_o = C.series_for(f"{t}_ours", t)[0]
    eq_o = ((1 + r_o).cumprod() - 1) * 100
    r_b = C.bh_returns(t)
    eq_b = ((1 + r_b).cumprod() - 1) * 100
    ax.plot(eq_o.index, eq_o.values, color=TCOL[t], lw=2.4, solid_capstyle="round", zorder=3)
    ax.plot(eq_b.index, eq_b.values, color=TCOL[t], lw=1.5, ls=(0, (5, 2)), alpha=0.6, zorder=2)
    ours_cr[t] = eq_o.iloc[-1]; bh_cr[t] = eq_b.iloc[-1]

ax.axhline(0, color="#999999", lw=0.9, ls=(0, (1, 2)))
ax.grid(True, axis="y", alpha=0.18)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.set_title("FinMem-Ours vs Buy & Hold — cumulative return by ticker (test window, 0 bps)",
             fontsize=13.5, fontweight="bold", color="#16215B", pad=12)
ax.set_ylabel("Cumulative return (%)")

handles = [Line2D([0], [0], color=TCOL[t], lw=2.6,
                  label=f"{t}   Ours {ours_cr[t]:+.1f}%   ·   B&H {bh_cr[t]:+.1f}%") for t in ORDER]
handles += [Line2D([0], [0], color="#555555", lw=2.4, label="solid = FinMem-Ours"),
            Line2D([0], [0], color="#555555", lw=1.5, ls=(0, (5, 2)), label="dashed = Buy & Hold")]
ax.legend(handles=handles, loc="lower left", fontsize=9.5, framealpha=0.92, borderpad=0.8)
om, bm = np.mean(list(ours_cr.values())), np.mean(list(bh_cr.values()))
ax.text(0.99, 0.04, f"mean   Ours {om:+.1f}%    B&H {bm:+.1f}%", transform=ax.transAxes,
        ha="right", va="bottom", color="#888888", fontsize=10.5)
fig.autofmt_xdate(); fig.tight_layout()
out = os.path.join(FIG, "finmem_ours_all_tickers_vs_bh.png")
fig.savefig(out, bbox_inches="tight"); plt.close(fig)
print("wrote", out)
