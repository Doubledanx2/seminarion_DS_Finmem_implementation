# Modernized from 03-model_wrapper.py (kept in repo for reference).
# Changes (see IMPLEMENTATION_LOG.md, B6):
#   1. Ported to openai>=1.0 client API (openai.ChatCompletion was removed in 1.0).
#   2. Removed the langchain_together path: the `Together` wrapper class shadowed the
#      imported `langchain_together.Together`, so the original could never have worked;
#      we only need the OpenAI family for the reproduction.
#   3. Added usage tracking so we can report actual token spend per run.

from abc import ABC, abstractmethod
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed

MAX_ATTEMPTS = 5
WAIT_TIME = 10


class Model_Wrapper(ABC):
    @retry(stop=stop_after_attempt(MAX_ATTEMPTS), wait=wait_fixed(WAIT_TIME))
    def summarize(self, text, summary_token_size=200):
        return self._summarize(text, summary_token_size)

    @abstractmethod
    def _summarize(self, text, summary_token_size):
        pass


class Chatgpt(Model_Wrapper):
    def __init__(self, key, model_name):
        self.client = OpenAI(api_key=key)
        self.model_name = model_name
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def _summarize(self, text, summary_token_size):
        prompt = f"Summarize the following news within {summary_token_size} tokens:\n{text}\nSummary:"
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        if response.usage:
            self.prompt_tokens += response.usage.prompt_tokens
            self.completion_tokens += response.usage.completion_tokens
        return response.choices[0].message.content


class Dummy(Model_Wrapper):
    """For test only"""
    import random
    import time

    def __init__(self, *args, **kwargs) -> None:
        print("Initializing a dummy model!")

    def _summarize(self, text, summary_token_size):
        self.time.sleep(self.random.randint(1, 5))
        if self.random.random() < 0.1:
            print("attempt", summary_token_size)
            raise RuntimeError("dummy random failure")
        return text[:summary_token_size]


class Model_Factory:
    registered_model_class = ("chatgpt", "dummy")

    @classmethod
    def create_model(cls, model_class: str, key: str = None, model_name: str = None, *args, **kwargs):
        assert model_class in cls.registered_model_class, \
            f"Invalid model class name: choose one from {cls.registered_model_class}"
        match model_class:
            case "chatgpt":
                return Chatgpt(key, model_name)
            case "dummy":
                return Dummy()
            case _:
                raise ValueError(model_class)
