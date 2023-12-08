import time
import re

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


def encode_node_titles(message, results):
    # Flatten nodes involved in the query
    returned_nodes = []
    all_nodes = []
    for result in results:
        if 'nodeset' in result:
            returned_nodes.extend(result['nodeset'])

        if 'nodesets' in result:
            for nodeset_name in result['nodesets']:
                nodeset = result['nodesets'][nodeset_name][:10]  # the LLM has seen at most 10 nodes from each nodeset
                all_nodes.extend(nodeset)

    # Remove duplicates
    returned_nodes = {(node['NodeType'], node['NodeKey']): node for node in returned_nodes}.values()
    all_nodes = {(node['NodeType'], node['NodeKey']): node for node in all_nodes}.values()

    # Create formatted answer with placeholders to replace names with links
    formatted_message = message
    formatting_dict = {}
    i = 0
    for node in all_nodes:
        # Match Markdown links like [Image processing II](Course/MICRO-512)
        pattern = (
                r"\[(.*?)\]"
                + r"\("
                + re.escape(node['NodeType'])
                + r"/"
                + re.escape(node['NodeKey'])
                + r"\)"
        )
        matches = re.findall(pattern, formatted_message)

        n_replacements = 0
        for match in matches:
            pattern = (
                    r"\["
                    + re.escape(match)
                    + r"\]"
                    + r"\("
                    + re.escape(node['NodeType'])
                    + r"/"
                    + re.escape(node['NodeKey'])
                    + r"\)"
            )
            formatted_message, n_match_replacements = re.subn(pattern, f'%{i}$', formatted_message)

            if n_match_replacements > 0:
                formatting_dict[i] = {**node, 'LinkText': match}
                n_replacements += n_match_replacements
                i += 1

        # If we have replaced something, we're done
        if n_replacements > 0:
            continue

        # If the node is not a returned node, we're done
        if node not in returned_nodes:
            continue

        # --- If we reach this, we haven't replaced Markdown links and the node is a returned one ---

        # We try to match only the node `Title`
        pattern = re.escape(node['Title'])
        formatted_message, n_replacements = re.subn(pattern, f'%{i}$', formatted_message)

        # If we have replaced something, we're done
        if n_replacements > 0:
            formatting_dict[i] = node
            i += 1

        # We try to match the node `Title` in lowercase as a last resource
        pattern = re.escape(node['Title'].lower())
        formatted_message, n_replacements = re.subn(pattern, f'%{i}$', formatted_message)

        # If we have replaced something, we're done
        if n_replacements > 0:
            formatting_dict[i] = node
            i += 1
            continue

    # Finally, remove any remaining (most likely malformed) Markdown links
    pattern = r"\[(.*?)\]\(.*?\)"
    formatted_message = re.sub(pattern, r'\1', formatted_message)

    return formatted_message, formatting_dict


def chat(conversation_id, human_input):
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

    # Replace node titles with placeholders so they can become links
    formatted_message, formatting_dict = encode_node_titles(message, results)
    print("[WRAPPER]", "Formatted message with placeholders for hyperlinks")

    return {
        'results': results,
        'message': message,
        'formatted_message': formatted_message,
        'formatting_dict': formatting_dict,
    }
