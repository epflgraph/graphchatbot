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

categories = {
    'help-with-assignment': {
        'description': "Requests that present an exercise or question and want help with its solution.",
        'system_prompt': """
# Pedagogical requirements
* Act as if you were a tutor or mentor for the user.
* Do not give the solution right away, but rather lay out directions or ask questions for the user to find the solution on their own.
* Your answer should help the user learn or understand.
* Do not use words or phrases that express doubt or provide a subjective opinion.
"""
    },

    'explain-concept': {
        'description': "Requests that ask a question about some specific concept or domain.",
        'system_prompt': """
# Pedagogical requirements
* Act as if you were an academic expert in the relevant domain.
* Your answer should help the user learn or understand.
* Do not use words or phrases that express doubt or provide a subjective opinion.
"""
    },

    'epfl-presidency': {
        'description': "Explicit requests about the presidency of EPFL.",
        'system_prompt': """
# Warning
Be careful with statements about people. Do not make any assumption that is not coming from the available information.
EPFL has one "President" and 6 "Vice Presidents", not to be confused with "Associate Vice Presidents".
""",
        'tool': 'search_news',
        'needs_orgchart': True,
    },

    'epfl-vice-presidencies': {
        'description': "Explicit requests about the vice-presidencies of EPFL.",
        'system_prompt': """
# Warning
Be careful with statements about people. Do not make any assumption that is not coming from the available information.
EPFL has one "President" and 6 "Vice Presidents", not to be confused with "Associate Vice Presidents".
""",
        'tool': 'search_news',
        'needs_orgchart': True,
    },

    'people': {
        'description': "Requests about researchers or instructors at EPFL.",
        'system_prompt': """
# Warning
Be careful with statements about people. Do not make any assumption that is not coming from the available information. After using the `search_nodes` tool to find information about a person, use the `search_news` tool to find news articles about them.
""",
        'needs_orgchart': True,
    },

    'legal-and-regulations': {
        'description': "Requests about regulations at EPFL, like recruiting, HR, contract management, sicknesses, accidents, absences, holidays, teleworking or internal processes.",
        'integration': 'lex',
        'tool': 'search_lex',
    },

    'lectures': {'description': "Requests about EPFL video lectures."},
    'exercises': {'description': "Requests that want to find exercises about some topic.", 'tool': 'search_exercises'},
    'courses': {'description': "Requests about EPFL courses."},

    'study-plan': {
        'description': "Requests about the EPFL study plan, for example about credits, pre-requisites or the availability of courses in a given plan.",
        'system_prompt': """
# Warning
Currently there is no information available about the study plan in the system. However, here are the [study plans in French](https://www.epfl.ch/education/studies/reglement-et-procedure/plans_etudes/) and [in English](https://www.epfl.ch/education/studies/en/rules-and-procedures/study_plans/).
"""
    },

    'schedule': {'description': "Student requests about the time schedule of the classes."},
    'student-projects': {'description': "Explicit requests about student projects."},
    'internships': {'description': "Explicit requests about student internships."},
    'labs-or-units': {'description': "Requests about EPFL units (labs, centers, institutes, chairs, etc.)."},
    'startups': {'description': "Explicit requests about EPFL startups or spin-off companies."},
    'news': {'description': "Explicit requests about news from EPFL.", 'tool': 'search_news'},
    'infrastructure': {'description': "Explicit requests about the infrastructure of EPFL, like rooms, buildings, toilets, showers, etc.", 'tool': 'search_plan'},
}


def get_category_description(category):
    # Return description for the given category
    return categories.get(category, {}).get('description', '')


def category_is_restricted(category):
    # Return whether a category is restricted
    return categories.get(category, {}).get('restricted', False)


def get_category_integration(category):
    # Return specific integration for the given category
    return categories.get(category, {}).get('integration')


def get_category_tool(category, integrations):
    category_integration = get_category_integration(category)

    # If category does not have any integration, it is unrestricted, we return its tool directly
    if not category_integration:
        return categories.get(category, {}).get('tool', 'search_nodes')

    # If category has an integration, and it is allowed, we return its tool directly
    if category_integration in integrations:
        return categories.get(category, {}).get('tool', 'search_nodes')

    # If category has an integration, but it is not allowed, we default to `search_nodes`
    return 'search_nodes'


def category_needs_orgchart(category):
    # Return whether a category needs the orgchart
    return categories.get(category, {}).get('needs_orgchart', False)


def get_category_system_prompt(category):
    # Return specific system prompt for the given category or default to None
    return categories.get(category, {}).get('system_prompt')


################################################################
# Model with schema                                            #
################################################################
class ConversationType(BaseModel, extra='allow'):
    model_config = {'json_schema_extra': {"additionalProperties": False}}

    category: Literal[*list(categories.keys())]


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
model = ChatOpenAI(model=model_name, temperature=0, openai_api_key=config['openai']['api_key'], request_timeout=60).bind(response_format=response_format)
parser = PydanticOutputParser(pydantic_object=ConversationType)


def classify_conversation(conversation, integrations):
    # Keep only Human and AI messages
    conversation = [m for m in conversation if isinstance(m, HumanMessage) or isinstance(m, AIMessage)]

    # Prepare system prompt
    categories_prompt = '\n'.join([f"* {category_name}: {get_category_description(category_name)}" for category_name in categories])

    system_prompt = f"""
You will be given a conversation between a Human and an AI system.
Your task is to classify the conversation based on what the last request is about. 
The possible categories are the following:
{categories_prompt}
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

    category = classify_conversation(messages, integrations=['lex'])

    print(category)
