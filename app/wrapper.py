"""
This module handles the interaction with the wrapper agent of the chatbot.
More specifically, it handles the management of langchain chains (creation, retrieval, deletion) and provides an entry point to interact with them.
"""

import time

from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage
from langchain.prompts.chat import MessagesPlaceholder
from langchain.agents import initialize_agent
from langchain.tools import StructuredTool

from app.config import config
from app.prompts import system_messages
from app.agents import CUSTOM_OPENAI_FUNCTIONS
from app.tools import ask_graph, search_exercises, find_color, search_news

################################################################
# CHAINS                                                       #
################################################################

# Initialise object to store chains
chains = {}
last_interactions = {}


def create_chain(memory_key):
    """
    Creates a wrapper agent chain with a given memory key to keep track of message history.

    Args:
        memory_key (str): Memory key identifier to uniquely identify the conversation.

    Returns:
        AgentExecutor: Langchain agent executor with all available tools to use, with memory to build a conversation after subsequent messages.
    """

    chat_llm = ChatOpenAI(temperature=0, openai_api_key=config['openai']['api_key'])

    tools = [
        StructuredTool.from_function(name='Ask_EPFL_Graph', func=ask_graph, description="Useful to ask the knowledge graph of EPFL in natural language"),
        StructuredTool.from_function(name='Search_EXOSET_Exercises', func=search_exercises, description="Useful to find references to exercises in EXOSET, the exercises database of EPFL, that are related to a given concept."),
        StructuredTool.from_function(name='Find_Person_Favourite_Color', func=find_color, description="Useful to find somebody's favourite color. Use sparingly and only when literally someone's favourite color is requested."),
        StructuredTool.from_function(name='Search_EPFL_News', func=search_news, description="Useful to fetch news articles from EPFL. Use sparingly and only when literally news are requested."),
    ]

    memory = ConversationBufferMemory(memory_key=memory_key, return_messages=True)

    agent_kwargs = {
        'system_message': SystemMessage(content=system_messages['wrapper']),        # system prompt of the agent
        'extra_prompt_messages': [MessagesPlaceholder(variable_name=memory_key)]    # placeholder for history messages
    }

    return initialize_agent(
        tools=tools,
        llm=chat_llm,
        agent=CUSTOM_OPENAI_FUNCTIONS,
        memory=memory,
        agent_kwargs=agent_kwargs,
        verbose=False,
        max_execution_time=30
    )


def delete_chain(memory_key=None):
    """
    Deletes the wrapper agent chain with a given memory key.

    Args:
        memory_key (str): Memory key identifier to uniquely identify the conversation to be deleted. If None, all chains are deleted.
    """

    if memory_key is None:
        print("[WRAPPER] Killing all chains")
        memory_keys = list(chains.keys())
        for memory_key in memory_keys:
            del chains[memory_key]
            del last_interactions[memory_key]

    elif memory_key in chains:
        print(f"[WRAPPER] Killing chain {memory_key}")
        del chains[memory_key]
        del last_interactions[memory_key]


def get_chain(memory_key):
    """
    Retrieves the wrapper agent chain with a given memory key.

    Args:
        memory_key (str): Memory key identifier to uniquely identify the conversation to be retrieved.

    Returns:
        AgentExecutor: Langchain agent executor identified by the memory key. If there is none, then one is created and returned.
    """

    # Clear memory if more than 5 minutes have passed
    if memory_key not in last_interactions:
        last_interactions[memory_key] = time.time()

    last = last_interactions[memory_key]
    now = time.time()
    if memory_key in chains and now - last >= 300:
        print(f"[WRAPPER] Killing chain {memory_key}")
        delete_chain(memory_key)

    last_interactions[memory_key] = now

    # Create new chain if it does not exist already
    if memory_key not in chains:
        chains[memory_key] = create_chain(memory_key)

    return chains[memory_key]


################################################################
# MAIN                                                         #
################################################################

def chat(conversation_id, human_input):
    """
    Sends a new message to the chatbot in the context of a given conversation.

    Args:
        conversation_id (str): ID of a conversation. Subsequent calls to the same conversation will keep the message history.
        If no conversation is found for the given ID, a new one will be created.
        human_input (str): Message written by the user to be sent to the chatbot.

    Returns:
        dict: Dictionary with keys `message` and `results`, containing the answer of the chatbot to the user's message and information about the
        returned nodes if applicable, respectively.
    """

    print("[WRAPPER]", f"Received chat request for input `{human_input}`")

    chain = get_chain(conversation_id)
    print("[WRAPPER]", f"Got chain for conversation `{conversation_id}`")

    message = chain.run(human_input)

    print("[WRAPPER]", "Got response message from agent executor")

    # Fetch results obtained in the tool
    if chain.agent.results:
        print("[WRAPPER]", "Successfully found results")
        results = chain.agent.results
    else:
        print("[WRAPPER]", "Could not find results from tool, defaulting to [].")
        results = []

    return {
        'message': message,
        'results': results,
    }
