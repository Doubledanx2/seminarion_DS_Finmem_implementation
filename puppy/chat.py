import os
import time
import httpx
import json
import subprocess
from abc import ABC
from datetime import datetime, timezone, timedelta
from typing import Callable, Union, Dict, Any, Union

### when use tgi model
api_key = '-'


class DailyQuotaExhausted(Exception):
    """Raised when the configured daily token budget is hit and wait_for_reset=false.
    run.py checkpoints every step, so the sim can be resumed after 00:00 UTC."""


class BudgetExhausted(Exception):
    """A3.2: raised when lifetime projected cost reaches the hard abort line ($4.00
    of the $5 account budget). Write a blocker to STATUS.md; do not continue."""


class TokenMeter:
    """Persistent per-UTC-day token/cost meter (ARCHITECTURE.md §6: meter mandatory).

    Tracks usage against the OpenAI data-sharing free pool (2.5M tok/day for mini
    models, resets 00:00 UTC). When the budget is exceeded: sleep until reset
    (wait_for_reset=True) or raise DailyQuotaExhausted (False).
    """

    # $/1M tokens, used for projected-cost accounting (A3.2)
    PRICES = {"gpt-4.1-mini": (0.40, 1.60), "gpt-4.1": (2.00, 8.00)}
    HARD_ABORT_USD = 4.00          # A3.2: abort line on the $5 account budget
    MAX_REQUEST_TOKENS = 16_000    # conservative per-request ceiling (prompt+completion)

    def __init__(
        self,
        path: str = os.path.join("data", "04_model_output_log", "openai_meter.json"),
        daily_token_budget: Union[int, None] = 2_400_000,
        wait_for_reset: bool = True,
        paid_overflow: bool = False,   # Stage 8: continue past the free pool on paid tokens
        paid_cap_usd: float = 3.00,    # hard cap on PAID chat spend (Dan-authorized)
    ) -> None:
        self.path = path
        self.daily_token_budget = daily_token_budget
        self.wait_for_reset = wait_for_reset
        self.paid_overflow = paid_overflow
        self.paid_cap_usd = paid_cap_usd
        self.state = {"utc_date": self._today(), "in_tokens": 0, "out_tokens": 0,
                      "calls": 0, "lifetime_in": 0, "lifetime_out": 0,
                      "paid_in": 0, "paid_out": 0}
        if os.path.exists(path):
            with open(path) as f:
                self.state = json.load(f)
        self.state.setdefault("paid_in", 0)
        self.state.setdefault("paid_out", 0)
        self._rollover()

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _rollover(self) -> None:
        if self.state["utc_date"] != self._today():
            self.state.update({"utc_date": self._today(), "in_tokens": 0,
                               "out_tokens": 0, "calls": 0})

    def projected_cost(self, model: str = "gpt-4.1-mini") -> float:
        """Worst-case lifetime spend if NONE of it was covered by the free pool."""
        base = next((k for k in self.PRICES if model.startswith(k)), "gpt-4.1-mini")
        pi, po = self.PRICES[base]
        return self.state["lifetime_in"] / 1e6 * pi + self.state["lifetime_out"] / 1e6 * po

    def paid_cost(self, model: str = "gpt-4.1-mini") -> float:
        """Actual PAID spend: only tokens consumed beyond the daily free pool."""
        base = next((k for k in self.PRICES if model.startswith(k)), "gpt-4.1-mini")
        pi, po = self.PRICES[base]
        return self.state["paid_in"] / 1e6 * pi + self.state["paid_out"] / 1e6 * po

    def check_budget(self, model: str = "gpt-4.1-mini") -> None:
        self._rollover()
        if self.paid_overflow:
            # Stage 8: explicit paid tracking supersedes the worst-case abort.
            if self.paid_cost(model) >= self.paid_cap_usd:
                raise BudgetExhausted(
                    f"PAID spend ${self.paid_cost(model):.2f} >= ${self.paid_cap_usd:.2f} "
                    f"hard cap — write blocker to STATUS.md")
            return  # never sleep: free pool first, then paid until the cap
        # A3.2 hard abort: projected (worst-case) spend reaches $4.00 of the $5 budget
        if self.projected_cost(model) >= self.HARD_ABORT_USD:
            raise BudgetExhausted(
                f"projected worst-case spend ${self.projected_cost(model):.2f} >= "
                f"${self.HARD_ABORT_USD:.2f} hard abort — write blocker to STATUS.md")
        if self.daily_token_budget is None:
            return
        # A3.2: never START a request that could overflow the remaining daily free
        # quota (an overflowing request is billed in full) — stop early instead
        used = self.state["in_tokens"] + self.state["out_tokens"]
        if used + self.MAX_REQUEST_TOKENS < self.daily_token_budget:
            return
        if not self.wait_for_reset:
            raise DailyQuotaExhausted(
                f"{used} tokens today + {self.MAX_REQUEST_TOKENS} headroom >= "
                f"budget {self.daily_token_budget}")
        now = datetime.now(timezone.utc)
        reset = (now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
        wait_s = (reset - now).total_seconds()
        print(f"[TokenMeter] daily budget hit; sleeping {wait_s / 3600:.1f}h until 00:05 UTC")
        time.sleep(wait_s)
        self._rollover()

    def add(self, model: str, usage: Dict[str, Any]) -> None:
        self._rollover()
        p, c = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        # Stage 8 paid-overflow accounting: a call that starts at or crosses the
        # free-pool boundary is counted ENTIRELY as paid, and the switchover is
        # logged explicitly (never straddle silently).
        if self.paid_overflow and self.daily_token_budget is not None:
            before = self.state["in_tokens"] + self.state["out_tokens"]
            if before + p + c > self.daily_token_budget:
                if self.state["paid_in"] == 0 and self.state["paid_out"] == 0:
                    print(f"[TokenMeter] PAID OVERFLOW STARTED at {before:,} tokens today "
                          f"(free pool {self.daily_token_budget:,}); cap ${self.paid_cap_usd:.2f}")
                elif before <= self.daily_token_budget:
                    print(f"[TokenMeter] boundary-straddling call counted fully as paid "
                          f"({before:,} -> {before + p + c:,})")
                self.state["paid_in"] += p
                self.state["paid_out"] += c
        self.state["in_tokens"] += p
        self.state["out_tokens"] += c
        self.state["lifetime_in"] += p
        self.state["lifetime_out"] += c
        self.state["calls"] += 1
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.state, f)
        base = next((k for k in self.PRICES if model.startswith(k)), None)
        if base and self.state["calls"] % 25 == 0:
            pi, po = self.PRICES[base]
            cost = self.state["lifetime_in"] / 1e6 * pi + self.state["lifetime_out"] / 1e6 * po
            print(f"[TokenMeter] today {self.state['in_tokens'] + self.state['out_tokens']:,} tok "
                  f"({self.state['calls']} calls) | lifetime ≈${cost:.2f} list-price")

def build_llama2_prompt(messages):
    startPrompt = "<s>[INST] "
    endPrompt = " [/INST]"
    conversation = []
    for index, message in enumerate(messages):
        if message["role"] == "system" and index == 0:
            conversation.append(f"<<SYS>>\n{message['content']}\n<</SYS>>\n\n")
        elif message["role"] == "user":
            conversation.append(message["content"].strip())
        else:
            conversation.append(f" [/INST] {message['content'].strip()}</s><s>[INST] ")

    return startPrompt + "".join(conversation) + endPrompt


class LongerThanContextError(Exception):
    pass

class ChatOpenAICompatible(ABC):
    def __init__(
        self,
        end_point: str,
        model="gemini-pro",
        system_message: str = "You are a helpful assistant.",
        other_parameters: Union[Dict[str, Any], None] = None,
    ):
        api_key = os.environ.get("OPENAI_API_KEY", "-")
        self.end_point = end_point
        self.model = model
        self.system_message = system_message
        
        
        if self.model.startswith("gemini-pro"):
            proc_result = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True)
            access_token = proc_result.stdout.strip()
            self.headers = {     "Authorization": f"Bearer {access_token}",
                                "Content-Type": "application/json",
                            }
        elif self.model.startswith("tgi"):
            self.headers = {
                        'Content-Type': 'application/json'
                    }   
        else:
            self.headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            self.other_parameters = {} if other_parameters is None else dict(other_parameters)

        # token meter / daily-quota config: ours + non-API keys must never reach the payload
        other = getattr(self, "other_parameters", None)
        meter_kwargs = {}
        if other is not None:
            other.pop("tokenization_model_name", None)
            if "daily_token_budget" in other:
                meter_kwargs["daily_token_budget"] = other.pop("daily_token_budget")
            if "wait_for_reset" in other:
                meter_kwargs["wait_for_reset"] = bool(other.pop("wait_for_reset"))
            if "paid_overflow" in other:
                meter_kwargs["paid_overflow"] = bool(other.pop("paid_overflow"))
            if "paid_cap_usd" in other:
                meter_kwargs["paid_cap_usd"] = float(other.pop("paid_cap_usd"))
        self.meter = TokenMeter(**meter_kwargs)

    def parse_response(self, response: httpx.Response) -> str:
        if self.model.startswith("gpt"):
            response_out = response.json()
            return response_out["choices"][0]["message"]["content"]
        elif self.model.startswith("gemini-pro"):
            response_out = response.json()
            return response_out["candidates"][0]["content"]["parts"][0]["text"]
        elif self.model.startswith("tgi"):
            response_out = response.json()#[0]
            return response_out["generated_text"]
        else:
            raise NotImplementedError(f"Model {self.model} not implemented")

    def guardrail_endpoint(self) -> Callable:
        def end_point(input: str, **kwargs) -> str:
            input_str = [
                    # {"role": "system", "content": f"{self.system_message}"},
                    {"role": "system", "content": "You are a helpful assistant only capable of communicating with valid JSON, and no other text."},
                    {"role": "user", "content": f"{input}"},
                ]
            
            if self.model.startswith("gemini-pro"):
                input_prompts = {"role": "USER",
                                "parts": { "text": input_str[1]["content"]}
                                    }
                payload = {"contents": input_prompts,
                            "generation_config": {
                                                "temperature": 0.2,
                                                "top_p": 0.1,
                                                "top_k": 16,
                                                "max_output_tokens": 2048,
                                                "candidate_count": 1,
                                                "stop_sequences": []
                                                },
                            "safety_settings": {
                                                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                                "threshold": "BLOCK_LOW_AND_ABOVE"
                                                }
                        }
                response = httpx.post(url = self.end_point, headers= self.headers, json=payload, timeout=600.0 )
                
            elif self.model.startswith("tgi"):
                llama_input_str = build_llama2_prompt(input_str)
                # print(llama_input_str)
                
                payload = {
                "inputs": llama_input_str,
                "parameters": {
                                "do_sample": True,
                                "top_p": 0.6,
                                "temperature": 0.8,
                                "top_k": 50,
                                "max_new_tokens": 256,
                                "repetition_penalty": 1.03,
                                "stop": ["</s>"]
                            }
                            }

                # payload = json.dumps(payload)
                response = httpx.post(
                    self.end_point, headers=self.headers, json=payload, timeout=600.0  # type: ignore
                )
            else:
                self.meter.check_budget(self.model)  # may sleep until 00:05 UTC or raise
                payload = {
                    "model": self.model,  # or another model like "gpt-4.0-turbo"
                    "messages": input_str,
                }
                payload.update(self.other_parameters)
                payload = json.dumps(payload)


                response = httpx.post(
                    self.end_point, headers=self.headers, data=payload, timeout=600.0  # type: ignore
                )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if (response.status_code == 422) and ("must have less than" in response.text):
                    raise LongerThanContextError
                else:
                    raise e

            if self.model.startswith("gpt"):
                usage = response.json().get("usage")
                if usage:
                    self.meter.add(self.model, usage)

            return self.parse_response(response)

        return end_point

