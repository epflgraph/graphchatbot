from abc import ABC, abstractmethod
import inspect

from typing import Optional, Literal

from pydantic import BaseModel

from langchain_openai import ChatOpenAI

from app.llms import (
    build_prompt_from_message_list,
    generate_structured_response,
)

from app.config import config

# List of RCP models that have been tested
# rcp_models = [
#     'meta-llama/Llama-4-Scout-17B-16E-Instruct',  <- works but doesn't sound very smart
#     'meta-llama/Llama-3.3-70B-Instruct',          <- works but is not very fast
#     'Qwen/Qwen3-32B',                             <- works and sounds convincing
#     'Qwen/Qwen2.5-VL-72B-Instruct',               <- works but is not very fast
#     'Qwen/Qwen3-30B-A3B-Instruct-2507',           <- works, seems fast enough and sounds convincing
#     'Qwen/Qwen3-30B-A3B-Thinking-2507',
#     'deepseek-ai/DeepSeek-R1-Distill-Llama-70B',  <- doesn't work with tool_choice
#     'deepseek-ai/DeepSeek-R1-Distill-Qwen-32B',   <- doesn't work with tool_choice
#     'swiss-ai/Apertus-70B-Instruct-2509',         <- no tool calling (confirmed by swissai) :/, also doesn't sound very smart
# ]


class IntegrationConfig(ABC):
    # Class-level contract
    name: Optional[str] = None
    index: Optional[str] = None
    available_tools: Optional[list[str]] = None
    light_model: Optional[ChatOpenAI] = ChatOpenAI(model='gpt-4o-mini', temperature=0, openai_api_key=config.get('openai', {})['api_key'], request_timeout=60)
    model: Optional[ChatOpenAI] = ChatOpenAI(model='gpt-4o-mini', temperature=0, openai_api_key=config.get('openai', {})['api_key'], request_timeout=60)
    groups: Optional[list] = None

    def __init_subclass__(cls):
        super().__init_subclass__()
        if not inspect.isabstract(cls):
            if not isinstance(getattr(cls, 'name', None), str):
                raise TypeError(f"{cls.__name__} must define a class variable 'name' of type str.")
            if not isinstance(getattr(cls, 'index', None), str):
                raise TypeError(f"{cls.__name__} must define a class variable 'index' of type str.")
            if not isinstance(getattr(cls, 'available_tools', None), list):
                raise TypeError(f"{cls.__name__} must define a class variable 'available_tools' of type list[str].")

    # Instance-level abstract contract
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        pass

    @property
    @abstractmethod
    def request_types(self) -> dict:
        pass

    # Factory methods
    @classmethod
    def all_subclasses(cls):
        subclasses = []
        for subclass in cls.__subclasses__():
            subclasses.append(subclass)
            subclasses.extend(subclass.all_subclasses())
        return subclasses

    @classmethod
    def from_name(cls, name):
        subclasses = {subclass.name: subclass for subclass in cls.all_subclasses() if subclass.name}
        subclass = subclasses.get(name)

        if subclass is None:
            # Default to 'graph-chat' if unknown
            subclass = subclasses.get('graph-chat')

        return subclass()

    @classmethod
    def list_integrations(cls):
        return [subclass.name for subclass in cls.all_subclasses() if subclass.name]

    # Convenience methods
    def request_type_tools(self, request_type):
        return self.request_types.get(request_type, {}).get('tools', [])

    def request_type_instructions(self, request_type):
        return self.request_types.get(request_type, {}).get('instructions')

    # Common classify method
    def classify(self, messages):
        # Return if no request types or messages
        if not self.request_types or not messages:
            return None

        # Prepare system prompt
        categories_prompt = '\n'.join(
            [f"* {request_type}: {self.request_types[request_type]['description']}" for request_type in self.request_types])
        system_prompt = f"""
You will be given a conversation between a Human and an AI system.
Your task is to classify the conversation based on the last request.
The possible categories are the following:
{categories_prompt}
"""
        # Prepare human prompt
        human_prompt = build_prompt_from_message_list(messages)

        # Prepare response format
        categories = self.request_types.keys()

        class ConversationType(BaseModel):
            category: Literal[*list(categories)]

        # Run LLM call
        conversation_type = generate_structured_response(self.light_model, system_prompt, human_prompt, ConversationType)

        return conversation_type.category

    def build_tools(self):
        return []

    # Default premodel method
    def premodel(self, messages):
        # Default logic for the premodel state of the agent
        pass

    # Default postmodel method
    def postmodel(self, messages):
        # Default logic for the postmodel state of the agent
        pass
