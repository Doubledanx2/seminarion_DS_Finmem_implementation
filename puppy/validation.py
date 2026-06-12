"""Addendum A1: minimal reimplementation of the guardrails-0.3.2 contract.

guardrails-ai 0.3.2 requires Python <3.11; rather than fight it on 3.12 we reproduce
its behavior exactly (logged deviation): pydantic schema per call, ONE re-ask on
validation failure (re-ask includes the model's failed output + the error, mirroring
guardrails), and on persistent failure the paper's fallback: train -> error record,
test -> "hold".

Every re-ask and every fallback is appended to data/04_model_output_log/
validation_events.jsonl -> guardrail failure rate per model becomes a reportable
metric (the paper never measured this; it quantifies a hidden Hold bias).
"""
import os
import json
import logging
from datetime import date
from typing import Any, Callable, Dict, List, Union

# overridable so test suites never pollute the production failure-rate log
EVENTS_PATH = os.environ.get(
    "VALIDATION_EVENTS_PATH",
    os.path.join("data", "04_model_output_log", "validation_events.jsonl"),
)


def _log_event(kind: str, symbol: str, cur_date: date, run_mode: str, detail: str) -> None:
    os.makedirs(os.path.dirname(EVENTS_PATH), exist_ok=True)
    with open(EVENTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "event": kind,  # "reask" | "fallback"
            "symbol": symbol,
            "date": str(cur_date),
            "run_mode": run_mode,
            "detail": detail[:500],
        }) + "\n")


def _extract_json(text: str) -> Dict[str, Any]:
    """Parse the model output as JSON, tolerating markdown fences and pre/post text."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        t = t[4:] if t.startswith("json") else t
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object found in output: {text[:200]!r}")
    return json.loads(t[start:end + 1])


def _validate(parsed: Dict[str, Any], run_mode: str,
              id_lists: Dict[str, List[int]]) -> Dict[str, Any]:
    """Apply the guardrails-0.3.2 contract:
    - test mode: investment_decision in {buy, sell, hold}
    - summary_reason: non-empty string
    - each cited memory id must be in the actually-retrieved id list for its layer
    Returns the canonicalized output dict; raises ValueError listing all problems.
    """
    errors = []
    out: Dict[str, Any] = {}

    if run_mode == "test":
        decision = parsed.get("investment_decision")
        if isinstance(decision, str) and decision.strip().lower() in ("buy", "sell", "hold"):
            out["investment_decision"] = decision.strip().lower()
        else:
            errors.append(f"investment_decision must be one of buy/sell/hold, got {decision!r}")

    reason = parsed.get("summary_reason")
    if isinstance(reason, str) and reason.strip():
        out["summary_reason"] = reason.strip()
    else:
        errors.append("summary_reason must be a non-empty string")

    for field, allowed in id_lists.items():
        raw = parsed.get(field)
        if raw is None:
            out[field] = None
            continue
        # accept int, list[int], or guardrails-style [{"memory_index": int}]
        if isinstance(raw, (int, str)):
            raw = [raw]
        ids = []
        for item in (raw if isinstance(raw, list) else [raw]):
            if isinstance(item, dict):
                item = item.get("memory_index")
            try:
                item = int(item)
            except (TypeError, ValueError):
                errors.append(f"{field}: non-integer id {item!r}")
                continue
            if item in allowed:
                ids.append(item)
            else:
                errors.append(f"{field}: id {item} not in retrieved ids {sorted(set(allowed))}")
        out[field] = [{"memory_index": i} for i in ids] or None

    if errors:
        raise ValueError("; ".join(errors))
    return out


def guarded_call(
    endpoint_func: Callable[[str], str],
    base_prompt: str,
    run_mode: str,                       # "train" | "test"
    id_lists: Dict[str, List[int]],      # field name -> retrieved id list
    logger: logging.Logger,
    cur_date: date,
    symbol: str,
    num_reasks: int = 1,
) -> Dict[str, Any]:
    """Call the LLM endpoint, validate, re-ask once on failure, fall back like the paper."""
    prompt = base_prompt
    last_output, last_error = "", ""
    for attempt in range(1 + num_reasks):
        try:
            last_output = endpoint_func(prompt)
            parsed = _extract_json(last_output)
            validated = _validate(parsed, run_mode, id_lists)
            if attempt > 0:
                logger.info(f"validation re-ask succeeded for {symbol} {cur_date}")
            return validated
        except (ValueError, json.JSONDecodeError) as e:
            last_error = str(e)
            logger.info(f"validation failed (attempt {attempt + 1}) for {symbol} {cur_date}: {last_error}")
            _log_event("reask" if attempt < num_reasks else "fallback",
                       symbol, cur_date, run_mode, last_error)
            # guardrails-style re-ask: include the failed output and the error
            prompt = (
                base_prompt
                + "\n\nYour previous response was:\n" + str(last_output)[:4000]
                + "\n\nIt failed validation with the following error(s):\n" + last_error
                + "\n\nRespond again with ONLY a corrected JSON object that fixes these errors."
            )

    # persistent failure -> paper's fallback (train: error record, test: hold)
    fallback: Dict[str, Any] = {field: None for field in id_lists}
    fallback["summary_reason"] = f"validation failed after {num_reasks + 1} attempts: {last_error}"
    if run_mode == "test":
        fallback["investment_decision"] = "hold"
    logger.info(f"validation fallback ({'hold' if run_mode == 'test' else 'error record'}) "
                f"for {symbol} {cur_date}")
    return fallback


def validation_stats() -> Dict[str, Any]:
    """Guardrail failure-rate report (new metric vs the paper)."""
    if not os.path.exists(EVENTS_PATH):
        return {"reasks": 0, "fallbacks": 0}
    reasks = fallbacks = 0
    by_symbol: Dict[str, Dict[str, int]] = {}
    with open(EVENTS_PATH, encoding="utf-8") as f:
        for line in f:
            ev = json.loads(line)
            d = by_symbol.setdefault(ev["symbol"], {"reasks": 0, "fallbacks": 0})
            if ev["event"] == "reask":
                reasks += 1
                d["reasks"] += 1
            else:
                fallbacks += 1
                d["fallbacks"] += 1
    return {"reasks": reasks, "fallbacks": fallbacks, "by_symbol": by_symbol}
