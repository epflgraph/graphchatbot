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
    light_model: ChatOpenAI = ChatOpenAI(
        base_url=config.get('rcp', {})['base_url'],
        model='Qwen/Qwen3-30B-A3B-Instruct-2507',
        openai_api_key=config.get('rcp', {})['api_key'],
        request_timeout=60,
        stream_usage=True,
    )
    model: ChatOpenAI = ChatOpenAI(
        base_url=config.get('rcp', {})['base_url'],
        model='Qwen/Qwen3-30B-A3B-Instruct-2507',
        openai_api_key=config.get('rcp', {})['api_key'],
        request_timeout=60,
        stream_usage=True,
    )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        module = sys.modules.get(cls.__module__)
        if module and getattr(module, '__file__', None):
            prompt_file = Path(module.__file__).parent / 'prompt.md'
            if prompt_file.exists():
                root = Path(__file__).parent  # app/bots/
                cls._prompt_template = resolve(prompt_file, root)

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
