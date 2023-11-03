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
from app.tools import ask_graph

################################################################
# CHAINS                                                       #
################################################################

# Initialise object to store chains
chains = {}
last_interactions = {}


def create_chain(memory_key):
    chat_llm = ChatOpenAI(temperature=0, openai_api_key=config['openai']['api_key'])

    tools = [StructuredTool.from_function(name='Ask_EPFL_Graph', func=ask_graph, description="useful to ask the knowledge graph of EPFL in natural language")]

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


def get_chain(memory_key):
    # Clear memory if more than 5 minutes have passed
    if memory_key not in last_interactions:
        last_interactions[memory_key] = time.time()

    last = last_interactions[memory_key]
    now = time.time()
    if memory_key in chains and now - last >= 300:
        print("Killing chain")
        del chains[memory_key]

    last_interactions[memory_key] = now

    # Create new chain if it does not exist already
    if memory_key not in chains:
        chains[memory_key] = create_chain(memory_key)

    return chains[memory_key]


################################################################
# MAIN                                                         #
################################################################


def encode_node_titles(message, results):
    # Create formatted answer with placeholders to replace names with links
    formatted_message = message
    formatting_dict = {}
    i = 0
    for result in results:
        for node in result['nodeset']:
            needle = f"{node['NodeType']} {node['NodeKey']}"
            formatted_message = formatted_message.replace(needle, f'%{i}$')
            formatting_dict[i] = node
            i += 1

    return formatted_message, formatting_dict


def chat(conversation_id, human_input):
    print("[WRAPPER]", f"Received chat request for input `{human_input}`")

    chain = get_chain(conversation_id)
    message = chain.run(human_input)

    print("[WRAPPER]", f"Got response message from agent executor")

    # Fetch results obtained in the tool
    if chain.agent.results_list:
        print("[WRAPPER]", "Successfully found results")
        results = chain.agent.results_list[-1]
    else:
        print("[WRAPPER]", "Could not find results from tool, defaulting to [].")
        results = []

    # Replace node titles with placeholders so they can become links
    formatted_message, formatting_dict = encode_node_titles(message, results)
    print("[WRAPPER]", f"Formatted message with placeholders for hyperlinks")

    return {
        'results': results,
        'message': message,
        'formatted_message': formatted_message,
        'formatting_dict': formatting_dict,
    }
