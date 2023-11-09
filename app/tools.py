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
    # # Keep only `NodeType` and `NodeKey` in nodeset
    # return {
    #     'nodeset': [{'NodeType': node['NodeType'], 'NodeKey': node['NodeKey']} for node in result['nodeset']],
    #     'context': result['context']
    # }

    # TODO obfuscate in a sensible way that the LLM can cope with
    return {key: result[key] for key in result if key != 'nodesets'}


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
    while retries_left > 0:
        retries_left -= 1

        # Ask LLM to generate instructions for input text
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

        result = {
            'nodeset': returned_nodeset[:10],
            'nodesets': nodesets,
            'context': context,
            'context_message': context_message,
        }

        # Make result available outside the tool
        graph_answers[human_input] = result
        print("[TOOL]", "Stored result for access outside the tool")

        # Obfuscate returned nodeset, send back to LLM only `NodeType` and `NodeKey`
        return obfuscate_result(result)

    # Give up after failing all retries
    # We still keep the failed result, to avoid failing all retries again in case we get the same input
    print("[TOOL]", f"Giving up after not getting a result after {max_retries} retries.")

    result = {'error_code': ec.ERR_TOO_MANY_RETRIES}

    # Make result available outside the tool
    graph_answers[human_input] = result
    print("[TOOL]", "Stored failed result for access outside the tool")

    return result
