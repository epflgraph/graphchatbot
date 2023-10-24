import traceback

import langchain
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

from app.prompts import system_messages
import app.error_codes as ec
from app.instructions import (
    parse_instructions,
    check_instructions,
    follow_instructions,
    build_context,
    build_context_message,
    build_retry_message,
)

################################################################

langchain.debug = False

################################################################
# CHAINS                                                       #
################################################################


def create_chain(type, memory_key):
    chat = ChatOpenAI(
        temperature=0,
        openai_api_key=config['openai']['api_key'],
    )
    memory = ConversationBufferMemory(memory_key=memory_key, return_messages=True)
    prompt = ChatPromptTemplate(messages=[
            SystemMessagePromptTemplate.from_template(system_messages[type]),
            MessagesPlaceholder(variable_name=memory_key),
            HumanMessagePromptTemplate.from_template("{input}")
    ])

    return LLMChain(
        llm=chat,
        prompt=prompt,
        verbose=False,
        memory=memory,
    )


def get_chain(type, memory_key):
    # Create new chain if it does not exist already
    if memory_key not in chains[type]:
        chains[type][memory_key] = create_chain(type, memory_key)

    # Roll memory, keep only last n messages
    n = 10
    chains[type][memory_key].memory.chat_memory.messages = chains[type][memory_key].memory.chat_memory.messages[:n]

    return chains[type][memory_key]


# Initialise object to store chains
chains = {type: {} for type in system_messages}


################################################################
# MAIN                                                         #
################################################################


def wrap_nlp(conversation_id, query, results):
    chain = get_chain('wrapper', conversation_id)

    llm_output = chain({'input': f"Query: {query}\nResults: {str(results)}"})

    return llm_output['text']


def conversation(conversation_id, text):
    # Fetch or create chain
    chain = get_chain('instructions', conversation_id)

    # Iterate trying to produce a result as long as there are retries left
    max_retries = 3
    retries = max_retries
    while retries > 0:
        retries -= 1

        # Ask LLM to generate instructions for input text
        print(text)
        instructions_str = chain({'input': text})['text']
        print(instructions_str)

        # Parse instructions from text to list of dict
        try:
            instructions = parse_instructions(instructions_str)
        except Exception as e:
            # If this fails, the LLM did not even return a syntactically correct set of instructions
            # The typical case for this is when the input is something like "dlifhaslkjfn"
            # We do not even retry and just return the error code and the message for display
            print('Error parsing instructions')
            traceback.print_exc()
            return {'error_code': ec.ERR_CANNOT_PARSE_INSTRUCTIONS, 'message': instructions_str}

        # --- If we reach this point, the instructions are syntactically correct ---

        # Check instructions and return error object on failure
        ok, error = check_instructions(instructions)

        # If the instructions are not ok, build a new input text and retry
        if not ok:
            print(f"Error {error['code']}")
            text = build_retry_message(error)
            continue

        # --- If we reach this point, the instructions are syntactic and semantically correct ---

        # We follow the instructions to get the nodesets that answer the prompt
        try:
            nodesets = follow_instructions(instructions)
        except Exception as e:
            # If this fails, some instruction failed in its execution
            # An example for this is when we run an "All" instruction with some unsupported field
            # We do retry with a generic retry message
            print('Error following instructions')
            text = build_retry_message()
            continue

        # --- If we reach this point, we successfully obtained a list of nodesets by following the instructions ---

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
            print('Error building context')
            traceback.print_exc()
            return {'error_code': ec.ERR_CANNOT_BUILD_CONTEXT}

        # --- If we reach this point, we successfully created the contexts for the returned nodesets ---

        # We return a list of objects with all the information
        results = [
            {
                'nodeset': nodeset,
                'context': context,
                'context_message': context_message
            }
            for nodeset, context, context_message in zip(nodesets, contexts, context_messages)
        ]
        return {'results': results}

    print(f"Giving up after not getting a result after {max_retries} retries.")
    return {'error_code': ec.ERR_TOO_MANY_RETRIES}
