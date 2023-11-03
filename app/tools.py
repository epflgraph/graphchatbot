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


def obfuscate_results(results):
    # Keep only `NodeType` and `NodeKey` in nodesets
    return [
        {
            'nodeset': [{'NodeType': node['NodeType'], 'NodeKey': node['NodeKey']} for node in result['nodeset']],
            'context': result['context']
        }
        for result in results
    ]


def ask_graph(human_input: str) -> dict:
    print("[TOOL]", f"Called ask graph tool with input `{human_input}`")

    # Check if result is cached
    if human_input in graph_answers:
        print("[TOOL]", f"Found cached result for input `{human_input}`, returning right away without calling LLM.")
        return obfuscate_results(graph_answers[human_input])

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

        # We follow the instructions to get the nodesets that answer the prompt
        try:
            nodesets = follow_instructions(instructions)
        except Exception as e:
            # If this fails, some instruction failed in its execution
            # An example for this is when we run an "All" instruction with some unsupported field
            # We do retry with a generic retry message
            print("[TOOL]", "Error following instructions")
            input = build_retry_message()
            continue

        # --- If we reach this point, we successfully obtained a list of nodesets by following the instructions ---
        print("[TOOL]", "Nodesets obtained")

        # We build context dictionaries and context messages based on instructions
        # (e.g. "showing People related to the Concept Urbanism")
        try:
            contexts = build_context(instructions)
            context_messages = build_context_message(instructions)

            if not isinstance(contexts, list):
                contexts = [contexts]

            if not isinstance(context_messages, list):
                context_messages = [context_messages]

        except Exception as e:
            print("[TOOL]", "Error building context")
            traceback.print_exc()
            return {'error_code': ec.ERR_CANNOT_BUILD_CONTEXT}

        # --- If we reach this point, we successfully created the contexts for the returned nodesets ---
        print("[TOOL]", "Contexts obtained")

        # Generate results
        results = [
            {
                'nodeset': nodeset[:10],
                'context': context,
                'context_message': context_message
            }
            for nodeset, context, context_message in zip(nodesets, contexts, context_messages)
        ]

        # Make results available outside the tool
        print("[TOOL]", "Storing results for access outside the tool")
        graph_answers[human_input] = results

        # Obfuscate returned nodeset, send back to LLM only `NodeType` and `NodeKey`
        return obfuscate_results(results)

    print("[TOOL]", f"Giving up after not getting a result after {max_retries} retries.")
    return {'error_code': ec.ERR_TOO_MANY_RETRIES}
