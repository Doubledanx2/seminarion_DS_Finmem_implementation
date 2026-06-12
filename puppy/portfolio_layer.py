"""Portfolio layer — OUR extension (isolated module, work-plan step 9).

After the 5 per-stock FinMem decisions on each TEST day, one gpt-4.1-mini call maps
(decisions + reasoning + current portfolio state) -> target weights.
Constraints enforced: long-only (w >= 0), sum(w) <= 1, cash allowed (= 1 - sum).
Validation mirrors the A1 contract: parse JSON, one re-ask carrying the failed
output + error, fallback = keep previous weights (no trade). Every call's
reasoning + weights (and every re-ask/fallback) is appended to a jsonl log.

The prompt is simple and FIXED — do not tune it after the freeze commit.
"""
import os
import json
import logging
from datetime import date
from typing import Callable, Dict, Any

TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
LOG_PATH = os.path.join("data", "04_model_output_log", "portfolio_layer.jsonl")

PROMPT_TEMPLATE = """You are a portfolio manager allocating a long-only equity portfolio across five stocks: TSLA, NFLX, AMZN, MSFT, COIN. Cash is allowed.

Today is {cur_date}. Your per-stock analysts reported:
{decision_block}

Current portfolio weights (fraction of equity):
{weights_block}

Decide target weights for today. Rules:
- Long-only: every weight must be >= 0.
- The weights may sum to at most 1.0; any remainder stays in cash.
- Prefer gradual changes over drastic reallocation unless analyst reasoning is strong.

Respond with ONLY a JSON object, no other text:
{{"weights": {{"TSLA": <float>, "NFLX": <float>, "AMZN": <float>, "MSFT": <float>, "COIN": <float>}}, "reasoning": "<2-4 sentences>"}}"""


def _validate(parsed: Dict[str, Any]) -> Dict[str, float]:
    w = parsed.get("weights")
    if not isinstance(w, dict):
        raise ValueError("missing 'weights' object")
    errors = []
    out = {}
    for t in TICKERS:
        v = w.get(t)
        if not isinstance(v, (int, float)):
            errors.append(f"{t}: weight missing or non-numeric ({v!r})")
            continue
        if v < -1e-9:
            errors.append(f"{t}: negative weight {v} (long-only)")
            continue
        out[t] = max(0.0, float(v))
    if errors:
        raise ValueError("; ".join(errors))
    total = sum(out.values())
    if total > 1.0 + 1e-6:
        raise ValueError(f"weights sum to {total:.4f} > 1.0")
    return out


def _log(record: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


class PortfolioAllocator:
    """One instance per test run. endpoint_func = ChatOpenAICompatible(...)
    .guardrail_endpoint() with model gpt-4.1-mini (same meter/guards as agents)."""

    def __init__(self, endpoint_func: Callable[[str], str],
                 logger: logging.Logger = None) -> None:
        self.endpoint = endpoint_func
        self.logger = logger or logging.getLogger(__name__)
        self.prev_weights: Dict[str, float] = {t: 0.0 for t in TICKERS}

    def allocate(self, cur_date: date,
                 decisions: Dict[str, Dict[str, str]]) -> Dict[str, float]:
        """decisions: {ticker: {"decision": "buy|sell|hold", "reason": str}}"""
        decision_block = "\n".join(
            f"- {t}: {d.get('decision', 'hold').upper()} — {str(d.get('reason', ''))[:300]}"
            for t, d in decisions.items()
        )
        weights_block = "\n".join(
            f"- {t}: {self.prev_weights.get(t, 0.0):.3f}" for t in TICKERS
        ) + f"\n- CASH: {max(0.0, 1.0 - sum(self.prev_weights.values())):.3f}"
        base_prompt = PROMPT_TEMPLATE.format(
            cur_date=cur_date, decision_block=decision_block, weights_block=weights_block
        )

        prompt = base_prompt
        last_out, last_err = "", ""
        for attempt in range(2):  # initial + one re-ask (A1 contract)
            try:
                last_out = self.endpoint(prompt)
                t = last_out.strip()
                if t.startswith("```"):
                    t = t.split("```")[1]
                    t = t[4:] if t.startswith("json") else t
                parsed = json.loads(t[t.find("{"): t.rfind("}") + 1])
                weights = _validate(parsed)
                _log({"date": str(cur_date), "event": "allocate", "attempt": attempt,
                      "decisions": decisions, "weights": weights,
                      "reasoning": str(parsed.get("reasoning", ""))[:1000]})
                self.prev_weights = weights
                return weights
            except (ValueError, json.JSONDecodeError) as e:
                last_err = str(e)
                self.logger.info(f"portfolio validation failed ({attempt + 1}/2) {cur_date}: {e}")
                _log({"date": str(cur_date), "event": "reask" if attempt == 0 else "fallback",
                      "error": last_err, "raw": str(last_out)[:500]})
                prompt = (base_prompt
                          + "\n\nYour previous response was:\n" + str(last_out)[:2000]
                          + "\n\nIt failed validation: " + last_err
                          + "\nRespond again with ONLY a corrected JSON object.")
        # fallback: hold previous weights (no trade today)
        self.logger.info(f"portfolio fallback (hold prev weights) {cur_date}")
        return dict(self.prev_weights)
