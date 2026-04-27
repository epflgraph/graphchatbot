import sys
from abc import ABC, abstractmethod
from datetime import datetime
from functools import cached_property
from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.state import CompiledStateGraph

from app.config import config
from app.bots.prompts import resolve


class BaseState(MessagesState):
    """Minimal state shared by all bots. Extend this in bot classes that need extra fields."""
    pass


class Bot(ABC):
    # Every subclass must define these
    name: str
    groups: list[str]

    # Subclasses may override these
    model: ChatOpenAI = ChatOpenAI(
        base_url=config.get("rcp", {})["base_url"],
        model="Qwen/Qwen3.6-35B-A3B",
        api_key=config.get("rcp", {})["api_key"],
        timeout=60,
        stream_usage=True,
        temperature=0.7,
        top_p=0.8,
        presence_penalty=1.5,
        extra_body={
            "top_k": 20,
            "min_p": 0.0,
            "repetition_penalty": 1.0,
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )

    light_model: ChatOpenAI = model

    @cached_property
    def _prompt_template(self) -> str:
        module = sys.modules[type(self).__module__]
        cls_dir = Path(module.__file__).parent
        root = Path(__file__).parent  # app/bots/
        return resolve('prompt', cls_dir, root)

    def prompt_context(self) -> dict:
        return {'today': datetime.now().strftime("%Y-%m-%d")}

    @property
    def prompt(self) -> str:
        return self._prompt_template.format(**self.prompt_context())

    @abstractmethod
    def build_graph(self) -> CompiledStateGraph: ...

    @cached_property
    def graph(self) -> CompiledStateGraph:
        return self.build_graph()
