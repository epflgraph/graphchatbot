from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage
from langchain.prompts.chat import MessagesPlaceholder
from langchain.agents import AgentType, initialize_agent
from langchain.tools import StructuredTool

from app.config import config
from app.prompts import system_messages
from app.tools import ask_graph, graph_answers

################################################################
# CHAINS                                                       #
################################################################


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
        agent=AgentType.OPENAI_FUNCTIONS,
        memory=memory,
        agent_kwargs=agent_kwargs,
        verbose=True,
        max_execution_time=30
    )


def get_chain(memory_key):
    # Create new chain if it does not exist already
    if memory_key not in chains:
        chains[memory_key] = create_chain(memory_key)

    return chains[memory_key]


# Initialise object to store chains
chains = {}

################################################################
# MAIN                                                         #
################################################################


def encode_node_titles(message, results):
    # Merge nodesets and sort by descending `Title` length to minimise string replacement issues
    all_nodes = [node for result in results for node in result['nodeset']]
    all_nodes = sorted(all_nodes, key=lambda node: len(node['Title']), reverse=True)

    # Create formatted answer with placeholders to replace names with links
    formatted_message = message
    formatting_dict = {}
    i = 0
    for node in all_nodes:
        formatted_message = formatted_message.replace(node['Title'], f'%{i}$')
        formatted_message = formatted_message.replace(node['Title'].lower(), f'%{i}$')
        formatting_dict[i] = node
        i += 1

    return formatted_message, formatting_dict


def chat(conversation_id, human_input):
    chain = get_chain(conversation_id)

    message = chain.run(human_input)

    # Fetch results obtained in the tool
    results = graph_answers.get(human_input, [])

    # Replace node titles with placeholders so they can become links
    formatted_message, formatting_dict = encode_node_titles(message, results)

    return {
        'results': results,
        'message': message,
        'formatted_message': formatted_message,
        'formatting_dict': formatting_dict,
    }
