"""Extended reflection — EXPLORATORY paper-intent reconstruction (Stage 5, Task 2).

The paper describes a second reflection type: each day the agent re-evaluates the
last M=7 trading days (its decisions + reasoning vs realized moves) and synthesizes
a durable insight into "long-term memory". The shipped code never implemented it.

Destination ambiguity (D-next): the paper's text says "long-term memory", but in the
shipped architecture the reflection layer is its own index and is the only layer the
authors ever write agent-generated text into (add_memory_reflection); the long layer's
decay/threshold regime would expel any insight within days (see DEEP_LAYER_TRACE.md).
We therefore default to the REFLECTION layer (conservative, consistent with shipped
write-paths) and make "long" available via config:
    [general] extended_reflection = true
              extended_reflection_target = "reflection" | "long"

Output contract (validation.py style): {"insight": str, "confidence": low|med|high};
one re-ask carrying the failed output + error; persistent failure -> skip the day
(logged as a fallback event). One extra LLM call per test day.
"""
import json
import logging
import numpy as np
from datetime import date
from typing import Any, Dict

from .validation import _log_event

PROMPT = """You are reviewing your own recent trading of {symbol}. Below are your last {n} trading days: your decision, your reasoning at the time, and the realized next-day return that followed.

{history_block}

Synthesize ONE durable insight about what is currently working or failing in your decision process for {symbol} — a lesson that should still matter weeks from now (not a restatement of any single day). Respond with ONLY a JSON object:
{{"insight": "<2-4 sentences>", "confidence": "low" | "med" | "high"}}"""


def _history_block(agent, cur_date: date, m: int) -> str:
    pf = agent.portfolio
    dates = list(pf.date_series)
    prices = list(pf.market_price_series)
    rows = []
    idx = {d: i for i, d in enumerate(dates)}
    past = [d for d in sorted(agent.reflection_result_series_dict) if d < cur_date][-m:]
    for d in past:
        refl = agent.reflection_result_series_dict.get(d) or {}
        decision = refl.get("investment_decision", "n/a")
        reason = str(refl.get("summary_reason", ""))[:220]
        ret = ""
        if d in idx and idx[d] + 1 < len(prices):
            r = (prices[idx[d] + 1] - prices[idx[d]]) / prices[idx[d]]
            ret = f"{r * +100:+.2f}%"
        rows.append(f"- {d}: decision={decision}, realized next-day return={ret or 'n/a'}, reasoning: {reason}")
    return "\n".join(rows)


def step(agent, cur_date: date, num_reasks: int = 1) -> Dict[str, Any]:
    """One extended-reflection call. Returns the validated insight dict or {}."""
    logger = agent.logger or logging.getLogger(__name__)
    m = agent.look_back_window_size
    history = _history_block(agent, cur_date, m)
    if not history:
        return {}
    base_prompt = PROMPT.format(symbol=agent.trading_symbol, n=m, history_block=history)

    prompt = base_prompt
    last_out, last_err = "", ""
    for attempt in range(1 + num_reasks):
        try:
            last_out = agent.guardrail_endpoint(prompt)
            t = last_out.strip()
            if t.startswith("```"):
                t = t.split("```")[1]
                t = t[4:] if t.startswith("json") else t
            parsed = json.loads(t[t.find("{"): t.rfind("}") + 1])
            insight = str(parsed.get("insight", "")).strip()
            conf = str(parsed.get("confidence", "")).strip().lower()
            if not insight:
                raise ValueError("insight must be a non-empty string")
            if conf not in ("low", "med", "high"):
                raise ValueError(f"confidence must be low/med/high, got {conf!r}")
            text = f"[extended reflection, confidence={conf}] {insight}"
            target = getattr(agent, "extended_reflection_target", "reflection")
            if target == "long":
                agent.brain.add_memory_long(symbol=agent.trading_symbol, date=cur_date, text=text)
            else:
                agent.brain.add_memory_reflection(symbol=agent.trading_symbol, date=cur_date, text=text)
            logger.info(f"extended reflection {cur_date}: ({conf}) {insight}")
            return {"insight": insight, "confidence": conf}
        except (ValueError, json.JSONDecodeError) as e:
            last_err = str(e)
            _log_event("reask" if attempt < num_reasks else "fallback",
                       agent.trading_symbol, cur_date, "test-ext-refl", last_err)
            prompt = (base_prompt
                      + "\n\nYour previous response was:\n" + str(last_out)[:2000]
                      + "\n\nIt failed validation: " + last_err
                      + "\nRespond again with ONLY a corrected JSON object.")
    logger.info(f"extended reflection skipped (validation failed) {cur_date}: {last_err}")
    return {}
