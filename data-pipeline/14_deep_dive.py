"""Stage-10 Part D: decision & memory deep-dive per ticker.
DEEP_DIVE_<TKR>.md x5 + DEEP_DIVE.md index. No API calls — sources:
  - test state_dict (decisions, reasoning, cited memory ids, portfolio series)
  - brain/*/universe_index.pkl (id -> layer/date/text/importance, end-state)
  - memory_events_<TKR>_ours_test.jsonl (layer-transition counts)
Cited-id resolution is from the END-STATE brain; ids purged mid-test are flagged.
"""
import os
import re
import sys
import json
import pickle

import numpy as np

sys.path.insert(0, os.getcwd())
TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
CITE_FIELDS = [("short_memory_index", "short"), ("middle_memory_index", "mid"),
               ("long_memory_index", "long"), ("reflection_memory_index", "reflection")]
LAYER_DIRS = {"short": "short_term_memory", "mid": "mid_term_memory",
              "long": "long_term_memory", "reflection": "reflection_memory"}


def brain_id_map(tag):
    base = f"data/07_test_model_output/{tag}/agent_1/brain"
    id2rec = {}
    for lname, ld in LAYER_DIRS.items():
        path = os.path.join(base, ld, "universe_index.pkl")
        if not os.path.exists(path):
            continue
        for sym, rec in pickle.load(open(path, "rb")).items():
            for m in rec["score_memory"]:
                id2rec[m["id"]] = {"layer": lname, "date": str(m["date"]),
                                   "text": m["text"], "imp": round(m["important_score"], 1)}
    return id2rec


def sentiment_of(text):
    m = re.search(r"positive score for this news is ([\d.]+).*?neutral score for this news is "
                  r"([\d.]+).*?negative score for this news is ([\d.]+)", text)
    if not m:
        return None
    pos, neu, neg = (float(m.group(i).rstrip(".")) for i in (1, 2, 3))
    lab = max((("positive", pos), ("neutral", neu), ("negative", neg)), key=lambda x: x[1])
    return f"{lab[0]} (p={pos:.2f}/neu={neu:.2f}/neg={neg:.2f})"


def clean_text(text):
    return re.sub(r"\s*The positive score for this news is.*$", "", text).strip()


def cited_ids(refl_day):
    out = []
    for fld, lname in CITE_FIELDS:
        for item in (refl_day.get(fld) or []):
            mid = item.get("memory_index") if isinstance(item, dict) else item
            if mid not in (None, -1):
                out.append((lname, mid))
    return out


def build(ticker):
    tag = f"{ticker}_ours"
    sd = pickle.load(open(f"data/07_test_model_output/{tag}/agent_1/state_dict.pkl", "rb"))
    refl = {d: r for d, r in sd["reflection_result_series_dict"].items() if d.year == 2026}
    pf = sd["portfolio"]
    price = dict(zip(pf.date_series, pf.market_price_series))
    days = sorted(d for d in refl if d in price)
    nxt = {d: days[i + 1] for i, d in enumerate(days[:-1])}
    id2rec = brain_id_map(tag)

    # per-day frame
    frame = []
    plist = [price[d] for d in days]
    for i, d in enumerate(days):
        mode = "seeking" if i < 3 else ("averse" if (plist[i] - plist[i - 3]) < 0 else "seeking")
        dec = refl[d].get("investment_decision", "hold")
        reason = str(refl[d].get("summary_reason", ""))
        ret = (price[nxt[d]] / price[d] - 1) * 100 if d in nxt else None
        act = pf.action_series.get(d, 0)
        frame.append({"date": d, "mode": mode, "decision": dec, "reason": reason,
                      "ret": ret, "action": act, "cited": cited_ids(refl[d]),
                      "contrib": (act * ret) if ret is not None else 0.0})

    L = []
    L.append(f"# DEEP DIVE — {ticker} (FinMem-Ours, test 2026-01-02 → 2026-06-01)\n")
    L.append(f"{len(days)} test days · cited-memory resolution is from the END-STATE brain "
             f"({len(id2rec)} memories survived); ids purged mid-test are flagged `[purged]`.\n")

    # 1. adaptive persona timeline
    averse = [f for f in frame if f["mode"] == "averse"]
    seeking = [f for f in frame if f["mode"] == "seeking"]
    switches = [(frame[i - 1], frame[i]) for i in range(1, len(frame))
                if frame[i]["mode"] != frame[i - 1]["mode"]]
    echo = sum(1 for f in frame if "risk-averse" in f["reason"] or "risk-seeking" in f["reason"])

    def mix(fs):
        from collections import Counter
        c = Counter(f["decision"] for f in fs)
        return f"{c.get('buy',0)} buy / {c.get('hold',0)} hold / {c.get('sell',0)} sell"

    # hit-rate: on averse days, did being defensive (flat/sold) avoid a next-day loss?
    av_eval = [f for f in averse if f["ret"] is not None]
    avoided = sum(1 for f in av_eval if f["action"] <= 0 and f["ret"] < 0)
    intoloss = sum(1 for f in av_eval if f["action"] > 0 and f["ret"] < 0)
    L.append("## 1. Adaptive-persona timeline (3-day cumulative-return rule)\n")
    L.append(f"- Risk-seeking days: {len(seeking)} ({mix(seeking)})")
    L.append(f"- Risk-averse days: {len(averse)} ({mix(averse)})")
    L.append(f"- Mode switches: {len(switches)} · reasoning text explicitly echoed a risk stance "
             f"on {echo}/{len(frame)} days")
    if av_eval:
        L.append(f"- Risk-averse hit-rate: on {len(av_eval)} averse days with a known outcome, the agent "
                 f"was flat/short into {avoided + intoloss} next-day losses — avoided (already flat) "
                 f"{avoided}, caught long {intoloss}.")
    # verbatim switch examples
    L.append("\n**Mode-switch examples (verbatim reasoning):**")
    shown = 0
    for prev, cur in switches:
        kw = "risk-averse" if cur["mode"] == "averse" else "risk-seeking"
        if kw in cur["reason"]:
            r = re.sub(r"\s+", " ", cur["reason"])[:420]
            pa = (f"3-day move into {cur['date']}: "
                  f"{(price[cur['date']]/price[days[days.index(cur['date'])-3]]-1)*100:+.1f}%")
            L.append(f"\n- **{cur['date']}** → *{cur['mode']}* ({prev['mode']}→{cur['mode']}; {pa}; "
                     f"decision **{cur['decision']}**, next-day {cur['ret']:+.1f}%):\n  > {r}")
            shown += 1
        if shown >= 4:
            break
    if shown == 0:
        L.append("\n_(No switch day echoed the stance verbatim; mode is from the 3-day return sign.)_")

    # 2. pivotal days
    ranked = sorted([f for f in frame if f["ret"] is not None], key=lambda x: x["contrib"])
    pivotal = ranked[:3] + ranked[-3:]
    sw_days = [c for _, c in switches][:4]
    seen = set(id(x) for x in pivotal)
    for s in sw_days:
        if id(s) not in seen:
            pivotal.append(s); seen.add(id(s))
    L.append("\n## 2. What the model leaned on (pivotal days)\n")
    for f in sorted(pivotal, key=lambda x: x["date"]):
        L.append(f"\n### {f['date']} — {f['mode']}, decision **{f['decision']}**, "
                 f"next-day {f['ret']:+.1f}% (contrib {f['contrib']:+.1f})")
        if not f["cited"]:
            L.append("_no memories cited_")
        for lname, mid in f["cited"][:6]:
            rec = id2rec.get(mid)
            if not rec:
                L.append(f"- `{lname}` id {mid} `[purged]`")
                continue
            senti = sentiment_of(rec["text"])
            txt = clean_text(rec["text"])[:240]
            L.append(f"- `{rec['layer']}` id {mid} ({rec['date']}"
                     + (f", {senti}" if senti else "") + f"): {txt}")
        n_un = sum(1 for _, mid in f["cited"] if mid not in id2rec)
        if n_un:
            L.append(f"_({n_un}/{len(f['cited'])} cited ids purged before end-state)_")

    # 3. extended reflections
    ext = sorted([(v["date"], mid, v["text"]) for mid, v in id2rec.items()
                  if "extended reflection" in v["text"]])
    cited_long = {mid for f in frame for (ln, mid) in f["cited"] if ln in ("long", "reflection")}
    ext_cited = [e for e in ext if e[1] in cited_long]
    L.append("\n## 3. Extended reflections that reached deep memory\n")
    L.append(f"{len(ext)} extended-reflection insights survived in deep/reflection layers; "
             f"{len(ext_cited)} were later retrieved AND cited in a subsequent decision.")
    for dt, mid, txt in ext[:5]:
        conf = re.search(r"confidence=(\w+)", txt)
        body = re.sub(r"^\[extended reflection[^\]]*\]\s*", "", txt)
        L.append(f"\n- **{dt}** (id {mid}, confidence {conf.group(1) if conf else '?'}"
                 + (", **cited later**" if mid in cited_long else "") + f"):\n  > {body[:360]}")

    # 4. memory-reliance profile
    from collections import Counter
    cite_counter = Counter()
    layer_counter = Counter()
    for f in frame:
        for lname, mid in f["cited"]:
            layer_counter[lname] += 1
            cite_counter[mid] += 1
    total_cites = sum(layer_counter.values())
    L.append("\n## 4. Memory-reliance profile\n")
    if total_cites:
        L.append("Citation share by layer: " + ", ".join(
            f"{ln} {100*layer_counter[ln]//total_cites}%" for ln in
            ["short", "mid", "long", "reflection"]) + f" (n={total_cites} citations).")
        top_id, top_n = cite_counter.most_common(1)[0]
        rec = id2rec.get(top_id)
        L.append(f"Most-cited memory: id {top_id} cited {top_n}× — "
                 + (f"`{rec['layer']}` ({rec['date']}): {clean_text(rec['text'])[:200]}"
                    if rec else "`[purged before end-state]`"))

    # 5. notable failures
    L.append("\n## 5. Notable failures\n")
    fails = []
    for f in frame:
        if f["ret"] is None:
            continue
        # bought into a clear next-day loss while citing negative-sentiment news
        senti_neg = any((id2rec.get(mid) and (s := sentiment_of(id2rec[mid]["text"]))
                         and s.startswith("negative")) for _, mid in f["cited"])
        if f["decision"] == "buy" and f["ret"] < -3 and senti_neg:
            fails.append((f, "bought into a >3% next-day drop while citing negative-sentiment news"))
        elif f["decision"] == "sell" and f["ret"] > 3:
            fails.append((f, "sold right before a >3% next-day gain"))
    for f, why in sorted(fails, key=lambda x: x[0]["ret"])[:3]:
        r = re.sub(r"\s+", " ", f["reason"])[:300]
        L.append(f"\n- **{f['date']}** — {why} (next-day {f['ret']:+.1f}%):\n  > {r}")
    if not fails:
        L.append("_No clear contradiction-failures detected by the heuristic._")

    out = f"DEEP_DIVE_{ticker}.md"
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    # summary stats for index
    return {"ticker": ticker, "days": len(days), "averse": len(averse),
            "switches": len(switches), "ext": len(ext), "ext_cited": len(ext_cited),
            "layer_share": dict(layer_counter), "survived": len(id2rec), "file": out}


if __name__ == "__main__":
    idx = []
    for t in TICKERS:
        if os.path.exists(f"data/07_test_model_output/{t}_ours/agent_1/state_dict.pkl"):
            idx.append(build(t))
            print(f"wrote DEEP_DIVE_{t}.md")
    I = ["# DEEP DIVE — index (FinMem-Ours decision & memory analysis)\n",
         "Per-ticker decision/memory deep-dives. Cited-memory text resolved from end-state brains.\n",
         "| Ticker | Test days | Risk-averse days | Mode switches | Ext-refl insights (cited later) | Memories survived | File |",
         "|---|---|---|---|---|---|---|"]
    for r in idx:
        I.append(f"| {r['ticker']} | {r['days']} | {r['averse']} | {r['switches']} | "
                 f"{r['ext']} ({r['ext_cited']}) | {r['survived']} | [{r['file']}]({r['file']}) |")
    I.append("\nSee `RESULTS_FINMEM_OURS.md` for performance metrics, `DEEP_LAYER_TRACE.md` "
             "for the as-shipped revolving-door finding (F2) that motivated FinMem-Ours' "
             "retention fixes.")
    open("DEEP_DIVE.md", "w", encoding="utf-8").write("\n".join(I) + "\n")
    print("wrote DEEP_DIVE.md")
