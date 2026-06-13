"""Show the NO-MEMORY prompts actually sent to the model, and render the portfolio-layer
equity graph recomputed CANONICALLY (full env series incl. terminal day). No API."""
import os
import sys
import json
import pickle
import importlib.util

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import toml

sys.path.insert(0, os.getcwd())
spec = importlib.util.spec_from_file_location("c16", os.path.join("data-pipeline", "16_canonical_metrics.py"))
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
from puppy import prompts as P  # noqa: E402

FIG = "data/09_results/figures"
os.makedirs(FIG, exist_ok=True)
TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
COL = {"port": "#0072B2", "ew": "#009E73"}
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "figure.facecolor": "white",
                     "axes.facecolor": "white", "font.size": 10})


# ---------- 1. NO-MEMORY prompts ----------
def nomem_prompt(ticker, day, refl_day, mode, persona):
    """Reconstruct the prompt sent under no_memory=true: retrieval returns empty, so
    reflection's placeholder path injects 'No <layer>-term information.' for every layer."""
    inv = P.test_investment_info_prefix.format(symbol=ticker, cur_date=day) + "\n"
    for lab in ["short", "mid", "long", "reflection"]:
        inv += f"The {lab}-term information:\n-1. No {lab}-term information.\n-1. No {lab}-term information.\n"
        if lab == "short":
            inv += P.test_sentiment_explanation[:150].strip() + "...\n"
        inv += "\n"
    inv += P.test_momentum_explanation[:140].strip() + "...\n"
    inv += (P.persona_averse if mode == "averse" else P.persona_seeking) + "\n"
    head = P.test_prompt.split("${investment_info}")[0].strip()
    return (f"PERSONA (character_string_test):\n{persona[:380].strip()}...\n\n"
            + head + "\n\n" + inv
            + '\n[JSON instruction] {"investment_decision": buy|sell|hold, "summary_reason": ..., '
            '"short_memory_index": null, "middle_memory_index": null, "long_memory_index": null, '
            '"reflection_memory_index": null}   <- no memory ids: retrieval returned empty')


def modes(ticker):
    px = C.env_prices(ticker); days = list(px.index); pl = px.values
    return {days[i]: ("averse" if i >= 3 and (pl[i] - pl[i - 3]) < 0 else "seeking")
            for i in range(len(days))}


tag = "NFLX_ours_nomem"
sd = pickle.load(open(f"data/07_test_model_output/{tag}/agent_1/state_dict.pkl", "rb"))
refl = {d: r for d, r in sd["reflection_result_series_dict"].items() if d.year == 2026}
mm = modes("NFLX")
persona = toml.load("config/nflx_finmem_ours_nomem_config.toml")["general"]["character_string_test"]
seek = next(d for d in sorted(refl) if mm.get(d) == "seeking")
av = next(d for d in sorted(refl) if mm.get(d) == "averse")

L = ["# No-memory prompts — what the ablation actually sent (NFLX)\n",
     "_no_memory=true: retrieval returns empty, so every memory block is the placeholder "
     "'No <layer>-term information.' The agent sees ONLY persona + momentum + risk line. "
     "Decision/reasoning below are the real saved outputs._\n"]
for lab, d in [("RISK-SEEKING", seek), ("RISK-AVERSE", av)]:
    L.append(f"\n## {lab} day — NFLX {d} → decision **{refl[d].get('investment_decision')}**\n")
    L.append("```\n" + nomem_prompt("NFLX", d, refl[d], mm[d], persona) + "\n```")
    L.append(f"\n**Model's reasoning (verbatim):** “{str(refl[d].get('summary_reason',''))[:500]}”\n")
open("data/09_results/nomem_prompts.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("wrote data/09_results/nomem_prompts.md")
print("\n=== NO-MEMORY PROMPT (NFLX", seek, ") ===\n")
print(nomem_prompt("NFLX", seek, refl[seek], mm[seek], persona))


# ---------- 2. portfolio equity, recomputed canonically ----------
pr = json.load(open("data/09_results/portfolio_layer_result.json", encoding="utf-8-sig"))
weights = pr["weights"]
px = {t: C.env_prices(t) for t in TICKERS}
all_days = sorted(px["TSLA"].index)
# simple next-day returns per ticker on the FULL env series (incl terminal day)
fwd = {t: (px[t].shift(-1) / px[t] - 1.0) for t in TICKERS}
wdays = sorted(pd.to_datetime(d).date() for d in weights)
port_r, ew_r, kept = [], [], []
for d in wdays:
    if d not in fwd["TSLA"].index or np.isnan(fwd["TSLA"].get(d, np.nan)):
        continue
    w = weights[str(d)]
    pr_d = sum(w.get(t, 0) * fwd[t].get(d, 0.0) for t in TICKERS)
    ew_d = float(np.mean([fwd[t].get(d, 0.0) for t in TICKERS]))
    port_r.append(pr_d); ew_r.append(ew_d); kept.append(d)
port_eq = np.cumprod([1 + r for r in port_r])
ew_eq = np.cumprod([1 + r for r in ew_r])
port_cr = float(port_eq[-1] - 1); ew_cr = float(ew_eq[-1] - 1)
print(f"\nCANONICAL portfolio CR {port_cr*100:+.1f}%  vs equal-weight B&H {ew_cr*100:+.1f}%  "
      f"({len(kept)} days, through {kept[-1]})")

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(kept, port_eq, color=COL["port"], lw=2.2, label=f"LLM portfolio allocator ({port_cr*100:+.1f}%)")
ax.plot(kept, ew_eq, color=COL["ew"], lw=2.2, ls="--", label=f"Equal-weight Buy & Hold ({ew_cr*100:+.1f}%)")
ax.axhline(1.0, color="grey", lw=0.7)
ax.set_title("Portfolio layer (our extension) — equity curve, canonical\n"
             "gpt-4.1-mini weekly weights over the 5 stocks vs equal-weight B&H")
ax.set_xlabel("date"); ax.set_ylabel("growth of $1"); ax.legend()
fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(os.path.join(FIG, "portfolio_equity.png"), bbox_inches="tight"); plt.close(fig)
print("wrote", os.path.join(FIG, "portfolio_equity.png"))
