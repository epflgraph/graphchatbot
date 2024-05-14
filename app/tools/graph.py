"""
This module contains the tool to search in the EPFL Graph in natural language, as well as handling the management of its associated langchain chain.
The tool receives a query in natural language (e.g. `publications in astrophysics`), and uses an LLM to generate a list of instructions
in a specific syntax (e.g. "
A = Search(Concept, Astrophysics)
B = Neighborhood(A, Publication)
Return(B, Publication)
"),
which are then followed deterministically on the graph to obtain a nodeset, which is then returned.

There are several reasons why this approach was chosen:
* The LLM does not need to have access to the graph.
* No need to set up a RAG system to retrieve the most likely nodes for the LLM to see.
* Fewer tokens are exchanged, which leads to less latency, cost and energy usage.
* Data privacy. The only information sent to the LLM is the user input, nothing else.
* Results can be cached, since we assume the same query will always give rise to the same set of instructions,
regardless of whether the data has changed.
* Certain very complicated or sensitive queries can be artificially cached if needed, again regardless of whether the data has changed.
* Sometimes we can recover from a wrong set of instructions and ask again thanks to the strict syntax.
* Protection against hallucinations. If the LLM hallucinates, either the instructions are invalid, and we return no nodes, or the instructions
produce a wrong nodeset. Even in that case, we can explain how it was constructed, and we are sure that the data comes from the graph.
"""

import traceback

from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

from app.config import config
import app.error_codes as ec
from app.interfaces.db import db_manager
from app.prompts import system_messages
from app.instructions import (
    parse_instructions,
    check_instructions,
    follow_instructions,
    build_context,
    build_context_message,
    build_retry_message,
)

################################################################
# CHAINS                                                       #
################################################################


def create_chain():
    chat = ChatOpenAI(
        temperature=0,
        openai_api_key=config['openai']['api_key'],
        request_timeout=10,
    )
    memory = ConversationBufferMemory(memory_key='memory', return_messages=True)
    prompt = ChatPromptTemplate(messages=[
            SystemMessagePromptTemplate.from_template(system_messages['instructions']),
            MessagesPlaceholder(variable_name='memory'),
            HumanMessagePromptTemplate.from_template("{input}")
    ])

    return LLMChain(
        llm=chat,
        prompt=prompt,
        verbose=False,
        memory=memory,
    )


################################################################
# MAIN                                                         #
################################################################

# Object to store full object to be recovered by the wrapper
graph_answers = {}


def obfuscate_result(result):
    # If error, keep full result
    if 'error_code' in result:
        return result

    # Build link for each node
    for node in result['nodeset']:
        node['Link'] = f"{config['graphsearch']['base_url']}/{node['NodeType'].lower()}/{node['NodeKey']}"

    return {
        'nodeset': result['nodeset'],
        'context': result['context'],
        'context_message': result['context_message'],
    }


def ask_graph(human_input: str) -> dict:
    print("[TOOL]", f"Called ask graph tool with input `{human_input}`")

    # Check if result is cached
    if human_input in graph_answers:
        print("[TOOL]", f"Found cached result for input `{human_input}`, returning right away without calling LLM.")
        return obfuscate_result(graph_answers[human_input])

    chain = create_chain()

    # Iterate trying to produce a result as long as there are retries left
    max_retries = 3
    retries_left = max_retries
    input = human_input
    use_persistent_cache = True
    while retries_left > 0:
        retries_left -= 1

        # Fetch instructions from persistent cache
        if use_persistent_cache:
            print("[TOOL]", f"Trying to fetch instructions from persistent cache for input `{input}`")
            instructions_str = db_manager.get(input)
            print("[TOOL] Got the following instructions")
            print(instructions_str)
            use_persistent_cache = False    # we only try to fetch from persistent cache the first time
        else:
            instructions_str = None

        # Ask LLM to generate instructions for input text
        if instructions_str is None:
            print("[TOOL]", f"Calling LLM for instructions for input `{input}`")
            instructions_str = chain({'input': input})['text']
            print("[TOOL] Got the following instructions")
            print(instructions_str)

        # Parse instructions from str to list of dict
        try:
            instructions = parse_instructions(instructions_str)
        except Exception as e:
            # If this fails, the LLM did not even return a syntactically correct set of instructions
            # The typical case for this is when the input is something like "dlifhaslkjfn"
            # We do not even retry and just return the error code and the message for display
            print("[TOOL]", "Error parsing instructions")
            traceback.print_exc()
            return {'error_code': ec.ERR_CANNOT_PARSE_INSTRUCTIONS, 'message': instructions_str}

        # --- If we reach this point, the instructions are syntactically correct ---
        print("[TOOL]", "Instructions parsed")

        # Check instructions and return error object on failure
        ok, error = check_instructions(instructions)

        # If the instructions are not ok, build a new input text and retry
        if not ok:
            print("[TOOL]", f"Error {error['code']}")
            input = build_retry_message(error)
            continue

        # --- If we reach this point, the instructions are syntactic and semantically correct ---
        print("[TOOL]", "Instructions checked")

        # We follow the instructions to get the nodeset that answers the prompt
        try:
            nodesets, returned_nodeset = follow_instructions(instructions)
        except Exception as e:
            # If this fails, some instruction failed in its execution
            # An example for this is when we run an "All" instruction with some unsupported field
            # We do retry with a generic retry message
            print("[TOOL]", "Error following instructions")
            input = build_retry_message()
            continue

        # --- If we reach this point, we successfully obtained a nodeset by following the instructions ---
        print("[TOOL]", f"Nodeset obtained ({len(returned_nodeset)} nodes)")

        # We build a context dictionary and a context message based on the instructions
        # (e.g. "Showing People related to the Concept Urbanism")
        try:
            context = build_context(instructions, nodesets)
            context_message = build_context_message(instructions, nodesets)

        except Exception as e:
            print("[TOOL]", "Error building context")
            traceback.print_exc()
            return {'error_code': ec.ERR_CANNOT_BUILD_CONTEXT}

        # --- If we reach this point, we successfully created the context for the returned nodeset ---
        print("[TOOL]", "Context obtained")

        # Only a subset of nodes is returned, depending on the node type
        try:
            node_type = returned_nodeset[0]['NodeType']
            n_nodes = 10 if node_type in ['Concept', 'Person'] else 5
        except Exception:
            n_nodes = 5

        result = {
            'nodeset': returned_nodeset[:n_nodes],
            'nodesets': nodesets,
            'context': context,
            'context_message': context_message,
            'instructions': instructions,
            'instructions_str': instructions_str,
        }

        # Make result available outside the tool
        graph_answers[human_input] = result
        print("[TOOL]", "Stored result for access outside the tool")

        # Store instructions in persistent cache
        db_manager.set(human_input, instructions_str)
        print("[TOOL]", "Stored instructions in persistent cache")

        # Obfuscate returned nodeset, send back to LLM only `NodeType` and `NodeKey`
        return obfuscate_result(result)

    # Give up after failing all retries
    # We still keep the failed result, to avoid failing all retries again in case we get the same input
    print("[TOOL]", f"Giving up after not getting a result after {max_retries} retries.")

    result = {
        'error_code': ec.ERR_TOO_MANY_RETRIES,
        'instructions': instructions or [],
        'instructions_str': instructions_str,
    }

    # Make result available outside the tool
    graph_answers[human_input] = result
    print("[TOOL]", "Stored failed result for access outside the tool")

    return result
