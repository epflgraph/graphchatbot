from abc import ABC, abstractmethod
from functools import cached_property

from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.state import CompiledStateGraph

from app.config import config


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

    @abstractmethod
    def build_graph(self) -> CompiledStateGraph: ...

    @cached_property
    def graph(self) -> CompiledStateGraph:
        return self.build_graph()
