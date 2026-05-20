import inspect
from abc import ABC, abstractmethod
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Optional

from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.state import CompiledStateGraph

from app.config import config
from app.bots.prompts import resolve

BOTS_ROOT = Path(__file__).parent


class BotState(MessagesState):
    category: Optional[str]
    tool_choice: Optional[str]


class Bot(ABC):
    name: str
    groups: list[str]

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

    model_nodes: tuple[str, ...] = ('model',)

    def prompt_context(self) -> dict:
        return {'today': datetime.now().strftime("%Y-%m-%d")}

    def prompt(self, name: str | None = None) -> str:
        cls_dir = Path(inspect.getfile(type(self))).parent
        template = resolve(name or 'prompt', cls_dir, BOTS_ROOT)
        return template.format(**self.prompt_context())

    @abstractmethod
    def build_graph(self) -> CompiledStateGraph: ...

    @cached_property
    def graph(self) -> CompiledStateGraph:
        return self.build_graph()
