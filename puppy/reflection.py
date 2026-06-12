# sourcery skip: dont-import-test-modules
# Addendum A1: guardrails-ai replaced by puppy/validation.py (same contract,
# modern implementation — guardrails 0.3.2 needs Python <3.11). The pydantic
# schema factories below were guardrails artifacts and are gone; the validation
# contract (choices, id-membership, one re-ask, train/test fallback) lives in
# validation.guarded_call.
from rich import print
import logging
from datetime import date
from .run_type import RunMode
from httpx import HTTPStatusError
from typing import List, Callable, Dict, Union, Any, Tuple
from .chat import LongerThanContextError
from .validation import guarded_call
from .prompts import (
    short_memory_id_desc,
    mid_memory_id_desc,
    long_memory_id_desc,
    reflection_memory_id_desc,
    train_prompt,
    train_memory_id_extract_prompt,
    train_trade_reason_summary,
    train_investment_info_prefix,
    test_prompt,
    test_trade_reason_summary,
    test_memory_id_extract_prompt,
    test_invest_action_choice,
    test_investment_info_prefix,
    test_sentiment_explanation,
    test_momentum_explanation,
    persona_seeking,
    persona_averse,
    as_shipped_persona_line,
)


def _id_lists(
    short_id_list: List[int],
    mid_id_list: List[int],
    long_id_list: List[int],
    reflection_id_list: List[int],
) -> Dict[str, List[int]]:
    """Field name -> retrieved-id list, the validation contract input."""
    return {
        "short_memory_index": short_id_list,
        "middle_memory_index": mid_id_list,
        "long_memory_index": long_id_list,
        "reflection_memory_index": reflection_id_list,
    }


def _json_instruction(run_mode: str, id_lists: Dict[str, List[int]]) -> str:
    """Replaces guardrails' ${gr.complete_json_suffix_v2}: spells out the exact JSON
    object, the allowed decision choices, and the allowed memory ids per layer."""
    layer_desc = {
        "short_memory_index": short_memory_id_desc,
        "middle_memory_index": mid_memory_id_desc,
        "long_memory_index": long_memory_id_desc,
        "reflection_memory_index": reflection_memory_id_desc,
    }
    fields = []
    if run_mode == "test":
        fields.append('"investment_decision": one of "buy" | "sell" | "hold"'
                      f' — {test_invest_action_choice}')
        fields.append(f'"summary_reason": string — {test_trade_reason_summary}')
    else:
        fields.append(f'"summary_reason": string — {train_trade_reason_summary}')
    for name, ids in id_lists.items():
        allowed = sorted(set(ids))
        fields.append(
            f'"{name}": list of objects {{"memory_index": <int>}} — {layer_desc[name]} '
            f"Allowed ids: {allowed}."
        )
    return (
        "Output ONLY a single valid JSON object (no markdown, no extra text) with exactly "
        "these fields:\n" + "\n".join(f"- {f}" for f in fields)
    )


def _format_memories(
    short_memory: Union[List[str], None] = None,
    short_memory_id: Union[List[int], None] = None,
    mid_memory: Union[List[str], None] = None,
    mid_memory_id: Union[List[int], None] = None,
    long_memory: Union[List[str], None] = None,
    long_memory_id: Union[List[int], None] = None,
    reflection_memory: Union[List[str], None] = None,
    reflection_memory_id: Union[List[int], None] = None,
) -> Tuple[
    List[str],
    List[int],
    List[str],
    List[int],
    List[str],
    List[int],
    List[str],
    List[int],
]:
    # add placeholder information if not memory is available
    # each memory has a duplicate because guardrails::ValidChoices does not support single choice
    if (short_memory is None) or len(short_memory) == 0:
        short_memory = ["No short-term information.", "No short-term information."]
        short_memory_id = [-1, -1]
    elif len(short_memory) == 1:
        short_memory = [short_memory[0], short_memory[0]]
        short_memory_id = [short_memory_id[0], short_memory_id[0]]  # type: ignore
    if (mid_memory is None) or len(mid_memory) == 0:
        mid_memory = ["No mid-term information.", "No mid-term information."]
        mid_memory_id = [-1, -1]
    elif len(mid_memory) == 1:
        mid_memory = [mid_memory[0], mid_memory[0]]
        mid_memory_id = [mid_memory_id[0], mid_memory_id[0]]  # type: ignore
    if (long_memory is None) or len(long_memory) == 0:
        long_memory = ["No long-term information.", "No long-term information."]
        long_memory_id = [-1, -1]
    elif len(long_memory) == 1:
        long_memory = [long_memory[0], long_memory[0]]
        long_memory_id = [long_memory_id[0], long_memory_id[0]]  # type: ignore
    if (reflection_memory is None) or len(reflection_memory) == 0:
        reflection_memory = [
            "No reflection-term information.",
            "No reflection-term information.",
        ]
        reflection_memory_id = [-1, -1]
    elif len(reflection_memory) == 1:
        reflection_memory = [reflection_memory[0], reflection_memory[0]]
        reflection_memory_id = [reflection_memory_id[0], reflection_memory_id[0]]  # type: ignore

    return (
        short_memory,
        short_memory_id,
        mid_memory,
        mid_memory_id,
        long_memory,
        long_memory_id,
        reflection_memory,
        reflection_memory_id,
    )


def _delete_placeholder_info(validated_output: Dict[str, Any]) -> Dict[str, Any]:
    if "reflection_memory_index" in validated_output and (
        (validated_output["reflection_memory_index"])
        and (validated_output["reflection_memory_index"][0]["memory_index"] == -1)
    ):
        del validated_output["reflection_memory_index"]
    if "long_memory_index" in validated_output and (
        (validated_output["long_memory_index"])
        and (validated_output["long_memory_index"][0]["memory_index"] == -1)
    ):
        del validated_output["long_memory_index"]
    if "middle_memory_index" in validated_output and (
        (validated_output["middle_memory_index"])
        and (validated_output["middle_memory_index"][0]["memory_index"] == -1)
    ):
        del validated_output["middle_memory_index"]
    if "short_memory_index" in validated_output and (
        (validated_output["short_memory_index"])
        and (validated_output["short_memory_index"][0]["memory_index"] == -1)
    ):
        del validated_output["short_memory_index"]

    return validated_output


def _add_momentum_info(momentum: int, investment_info: str, window: int = 3) -> str:
    # FinMem-Ours passes window=7 (M-day cumulative return); as-shipped default 3
    if momentum == -1:
        investment_info += (
            f"The cumulative return of past {window} days for this stock is negative."
        )

    elif momentum == 0:
        investment_info += (
            f"The cumulative return of past {window} days for this stock is zero."
        )

    elif momentum == 1:
        investment_info += (
            f"The cumulative return of past {window} days for this stock is positive."
        )

    return investment_info


def _train_response_model_invest_info(
    cur_date: date,
    symbol: str,
    future_record: Dict[str, float | str],
    short_memory: List[str],
    short_memory_id: List[int],
    mid_memory: List[str],
    mid_memory_id: List[int],
    long_memory: List[str],
    long_memory_id: List[int],
    reflection_memory: List[str],
    reflection_memory_id: List[int],
):
    # validation contract: field -> allowed ids (was: guardrails pydantic factory)
    response_model = _id_lists(
        short_id_list=short_memory_id,
        mid_id_list=mid_memory_id,
        long_id_list=long_memory_id,
        reflection_id_list=reflection_memory_id,
    )
    # investment info + memories
    investment_info = train_investment_info_prefix.format(
        cur_date=cur_date, symbol=symbol, future_record=future_record
    )
    if short_memory:
        investment_info += "The short-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(short_memory_id, short_memory)]
        )
        investment_info += "\n\n"
    if mid_memory:
        investment_info += "The mid-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(mid_memory_id, mid_memory)]
        )
        investment_info += "\n\n"
    if long_memory:
        investment_info += "The long-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(long_memory_id, long_memory)]
        )
        investment_info += "\n\n"
    if reflection_memory:
        investment_info += "The reflection-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(reflection_memory_id, reflection_memory)]
        )
        investment_info += "\n\n"

    return response_model, investment_info


def _test_response_model_invest_info(
    cur_date: date,
    symbol: str,
    short_memory: List[str],
    short_memory_id: List[int],
    mid_memory: List[str],
    mid_memory_id: List[int],
    long_memory: List[str],
    long_memory_id: List[int],
    reflection_memory: List[str],
    reflection_memory_id: List[int],
    momentum: Union[int, None] = None,
    momentum_window: int = 3,
):
    # validation contract: field -> allowed ids (was: guardrails pydantic factory)
    response_model = _id_lists(
        short_id_list=short_memory_id,
        mid_id_list=mid_memory_id,
        long_id_list=long_memory_id,
        reflection_id_list=reflection_memory_id,
    )
    # investment info + memories
    investment_info = test_investment_info_prefix.format(
        symbol=symbol, cur_date=cur_date
    )
    if short_memory:
        investment_info += "The short-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(short_memory_id, short_memory)]
        )
        investment_info += test_sentiment_explanation
        investment_info += "\n\n"
    if mid_memory:
        investment_info += "The mid-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(mid_memory_id, mid_memory)]
        )
        investment_info += "\n\n"
    if long_memory:
        investment_info += "The long-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(long_memory_id, long_memory)]
        )
        investment_info += "\n\n"
    if reflection_memory:
        investment_info += "The reflection-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(reflection_memory_id, reflection_memory)]
        )
        investment_info += "\n\n"
    if momentum:
        investment_info += test_momentum_explanation
        investment_info = _add_momentum_info(momentum, investment_info, momentum_window)

    return response_model, investment_info


def trading_reflection(
    cur_date: date,
    endpoint_func: Callable[[str], str],
    symbol: str,
    run_mode: RunMode,
    logger: logging.Logger,
    momentum: Union[int, None] = None,
    momentum_window: int = 3,               # FinMem-Ours: 7 (M-day cumulative return)
    persona_risk: Union[str, None] = None,  # B8: None=as-shipped | "seeking" | "averse"
    future_record: Union[Dict[str, float | str], None] = None,
    short_memory: Union[List[str], None] = None,
    short_memory_id: Union[List[int], None] = None,
    mid_memory: Union[List[str], None] = None,
    mid_memory_id: Union[List[int], None] = None,
    long_memory: Union[List[str], None] = None,
    long_memory_id: Union[List[int], None] = None,
    reflection_memory: Union[List[str], None] = None,
    reflection_memory_id: Union[List[int], None] = None,
) -> Dict[str, Any]:
    # format memories
    (
        short_memory,
        short_memory_id,
        mid_memory,
        mid_memory_id,
        long_memory,
        long_memory_id,
        reflection_memory,
        reflection_memory_id,
    ) = _format_memories(
        short_memory=short_memory,
        short_memory_id=short_memory_id,
        mid_memory=mid_memory,
        mid_memory_id=mid_memory_id,
        long_memory=long_memory,
        long_memory_id=long_memory_id,
        reflection_memory=reflection_memory,
        reflection_memory_id=reflection_memory_id,
    )

    if run_mode == RunMode.Train:
        response_model, investment_info = _train_response_model_invest_info(
            cur_date=cur_date,
            symbol=symbol,
            future_record=future_record,  # type: ignore
            short_memory=short_memory,
            short_memory_id=short_memory_id,
            mid_memory=mid_memory,
            mid_memory_id=mid_memory_id,
            long_memory=long_memory,
            long_memory_id=long_memory_id,
            reflection_memory=reflection_memory,
            reflection_memory_id=reflection_memory_id,
        )
        cur_prompt = train_prompt
    else:
        response_model, investment_info = _test_response_model_invest_info(
            cur_date=cur_date,
            symbol=symbol,
            short_memory=short_memory,
            short_memory_id=short_memory_id,
            mid_memory=mid_memory,
            mid_memory_id=mid_memory_id,
            long_memory=long_memory,
            long_memory_id=long_memory_id,
            reflection_memory=reflection_memory,
            reflection_memory_id=reflection_memory_id,
            momentum=momentum,
            momentum_window=momentum_window,
        )
        cur_prompt = test_prompt

    # B8 paper-rule variant: swap the static as-shipped persona line for the
    # two-sided rule sentence selected by the lookback cumulative-return sign
    if persona_risk is not None and run_mode == RunMode.Test:
        replacement = persona_seeking if persona_risk == "seeking" else persona_averse
        cur_prompt = cur_prompt.replace(as_shipped_persona_line, replacement)

    # prompt + validated output (A1: validation.guarded_call replaces gd.Guard,
    # same contract: one re-ask with failed output + error, then paper fallback)
    mode_str = "train" if run_mode == RunMode.Train else "test"
    full_prompt = cur_prompt.replace("${investment_info}", investment_info).replace(
        "${gr.complete_json_suffix_v2}", _json_instruction(mode_str, response_model)
    )

    try:
        validated_output = guarded_call(
            endpoint_func=endpoint_func,
            base_prompt=full_prompt,
            run_mode=mode_str,
            id_lists=response_model,
            logger=logger,
            cur_date=cur_date,
            symbol=symbol,
            num_reasks=1,
        )
        return _delete_placeholder_info(validated_output)

    except Exception as e:
        if isinstance(e.__context__, LongerThanContextError) or isinstance(
            e, LongerThanContextError
        ):
            raise LongerThanContextError from e
        # B16 (Dan): the original returned {} silently here — the day vanished from
        # the failure-rate metric. Log the traceback as a fallback event and return
        # an EXPLICIT hold-fallback (test) / error record (train).
        import traceback
        from .validation import _log_event

        tb = traceback.format_exc()
        logger.error(f"trading_reflection exception for {symbol} {cur_date}:\n{tb}")
        mode_str = "train" if run_mode == RunMode.Train else "test"
        _log_event("fallback", symbol, cur_date, mode_str, f"exception: {tb}")
        fallback: Dict[str, Any] = {
            "summary_reason": f"exception fallback: {type(e).__name__}: {e}",
            "short_memory_index": None, "middle_memory_index": None,
            "long_memory_index": None, "reflection_memory_index": None,
        }
        if run_mode == RunMode.Test:
            fallback["investment_decision"] = "hold"
        return fallback
