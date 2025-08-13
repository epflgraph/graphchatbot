from abc import ABC, abstractmethod
import inspect

from typing import Optional, Literal

from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
)
from langchain.output_parsers import PydanticOutputParser


from app.config import config


class IntegrationConfig(ABC):
    # Class-level contract
    name: Optional[str] = None
    index: Optional[str] = None
    available_tools: Optional[list[str]] = None
    model: Optional[str] = 'gpt-4o-mini'
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
        human_prompt = []
        for message in messages:
            # Extract only text from messages to send (otherwise images or other media types can fill the context window)
            if isinstance(message.content, str):
                message_content = message.content
            else:
                message_content = '\n'.join([content_piece['text'] for content_piece in message.content if content_piece['type'] == 'text'])

            human_prompt.append(f'----{message.type.upper()}----\n{message_content}')
        human_prompt = '\n\n'.join(human_prompt)

        # Prepare response format
        categories = self.request_types.keys()

        class ConversationType(BaseModel, extra='allow'):
            model_config = {'json_schema_extra': {'additionalProperties': False}}

            category: Literal[*list(categories)]

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "conversation_type",
                "strict": True,
                "schema": ConversationType.model_json_schema()
            }
        }

        # Instantiate chat model and output parser
        model_name = 'gpt-4o-mini'
        model = ChatOpenAI(model=model_name, temperature=0, openai_api_key=config['openai']['api_key'], request_timeout=60)
        model = model.bind(response_format=response_format)
        parser = PydanticOutputParser(pydantic_object=ConversationType)

        # Gather the messages for the LLM input
        input_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]

        # Send request to LLM
        try:
            output = model.invoke(input=input_messages)
        except Exception as e:
            print('[CLASSIFY]', "ERROR: LLM API call failed")
            print('[CLASSIFY]', e)
            return None

        # Parse output
        try:
            conversation_type = parser.parse(output.content)
        except Exception as e:
            print('[CLASSIFY]', "ERROR: Parsing LLM response failed")
            print('[CLASSIFY]', output.content)
            print('[CLASSIFY]', e)
            return None

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
