"""
This module contains a function to classify a conversation (list of messages) via an LLM
"""

from typing import Literal
from pydantic import BaseModel

from langchain_openai import ChatOpenAI

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
)
from langchain.output_parsers import PydanticOutputParser

from app.config import config

################################################################
# Categories                                                   #
################################################################

conversation_categories = [
    'help-with-assigment',
    'explain-concept',
    'lectures',
    'exercises',
    'courses',
    'study-plan',
    'schedule',
    'student-projects',
    'internships',
    'labs-or-units',
    'startups',
    'news',
    'infrastructure',
]


def get_category_tool(category):
    if category == 'exercises':
        return 'search_exercises'

    if category == 'news':
        return 'search_news'

    if category == 'infrastructure':
        return 'search_plan'

    return 'search_nodes'


################################################################
# Model with schema                                            #
################################################################

class ConversationType(BaseModel, extra='allow'):
    model_config = {'json_schema_extra': {"additionalProperties": False}}

    category: Literal[*conversation_categories]


response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "conversation_type",
        "strict": True,
        "schema": ConversationType.model_json_schema()
    }
}

# Instantiate chat model and parser
model_name = 'gpt-4o-mini'
model = ChatOpenAI(model=model_name, temperature=0, openai_api_key=config['openai']['api_key'], request_timeout=30).bind(response_format=response_format)
parser = PydanticOutputParser(pydantic_object=ConversationType)


def classify_conversation(conversation):
    # Keep only Human and AI messages
    conversation = [m for m in conversation if isinstance(m, HumanMessage) or isinstance(m, AIMessage)]

    # Prepare system prompt
    conversation_categories_str = '\n'.join([f'* {category}' for category in conversation_categories])
    system_prompt = f"""
You will be given a conversation between a Human and an AI system.
Your task is to classify the conversation based on what the last request is about. 
The possible categories are the following:
{conversation_categories_str}
"""

    # Prepare human prompt
    human_prompt = '\n\n'.join([f'{conversation_message.type}: {conversation_message.content}' for conversation_message in conversation])

    # Gather the messages for the LLM input
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]

    # Send request to LLM
    try:
        output = model.invoke(input=messages)
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


if __name__ == '__main__':
    messages = [
        HumanMessage(content="A partir des données envoyées par l'engin spatial Voyager en 1979, l'ingénieur Linda Morabitoa découvert sur Io, un satellite de Jupiter, la première activité volcanique extraterrestre. Le panache de l'éruption s'élevait à 280 km d'altitude environ. Sachant que l'accélération due à la gravité à la surface de Io vaut 1.8 m·s^(−2), et supposant qu'elle demeure constante jusqu'à la hauteur maximale du panache, déterminez: 1. La vitesse à laquelle les débris étaient projetés? 2. Le temps qu'il leur fallait pour atteindre la hauteur maximale?"),
    ]

    category = classify_conversation(messages)

    print(category)
