"""
This module contains a function to generate via LLM a query meant to search in elasticsearch that summarises a list of messages
"""

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
# LLM expert                                                   #
################################################################


class WikipageList(BaseModel, extra='allow'):
    model_config = {'json_schema_extra': {"additionalProperties": False}}

    titles: list[str]


response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "wikipage_list",
        "strict": True,
        "schema": WikipageList.model_json_schema()
    }
}

# Instantiate chat model and parser
model_name = 'gpt-4o-mini'
model = ChatOpenAI(model=model_name, temperature=0, openai_api_key=config['openai']['api_key'], request_timeout=30).bind(response_format=response_format)
parser = PydanticOutputParser(pydantic_object=WikipageList)


def call_llm(conversation):
    # Prepare system prompt
    system_prompt = """
You will be given a conversation between two agents A and B.
Your task is to suggest up to three Wikipedia pages that represent the concepts discussed in the conversation.
They should therefore be short, concise and without any mathematical formula or urls.
    """

    # Prepare human prompt
    agents = {'Human': 'A', 'AI': 'B'}
    human_prompt = '\n\n'.join([f"{agents[conversation_message['role']]}: {conversation_message['content']}" for conversation_message in conversation])

    # Gather the messages for the LLM input
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]

    # Send request to LLM
    try:
        output = model.invoke(input=messages)
    except Exception as e:
        print('[ENTRY]', "ERROR: LLM API call failed")
        print('[ENTRY]', e)
        return None

    # Parse output
    try:
        keywords_list = parser.parse(output.content)
    except Exception as e:
        print('[ENTRY]', "ERROR: Parsing LLM response failed")
        print('[ENTRY]', output.content)
        print('[ENTRY]', e)
        return None

    return keywords_list.titles


def get_keywords_from_messages(messages):
    # Keep only Human and AI messages, and transform message to simpler dict form
    message_dicts = []
    for message in messages:
        if isinstance(message, HumanMessage):
            message_dicts.append({'role': 'Human', 'content': message.content})
        elif isinstance(message, AIMessage):
            message_dicts.append({'role': 'AI', 'content': message.content})

    return call_llm(message_dicts)


if __name__ == '__main__':
    messages = [
        HumanMessage(content="hey show me lectures on electromagnetism"),
        AIMessage(content="Sure! Here are some lectures on electromagnetism:\n* [Maxwell's equations](https://graphsearch.epfl.ch/lecture/0_af43e837)\n* [Electric and Magnetic fields](https://graphsearch.epfl.ch/lecture/0_b238c923)\n* [Trajectories under electromagnetic forces](https://graphsearch.epfl.ch/lecture/0_6d7a194a)\nFeel free to ask more about these lectures or about a different topic!")
    ]

    query = get_keywords_from_messages(messages)

    print(query)
