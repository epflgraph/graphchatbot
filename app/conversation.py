import traceback

import langchain
from langchain.callbacks import get_openai_callback
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

from app.interfaces.es import search_nodes
from app.interfaces.db import update_token_count

from app.prompts import system_messages
from app.nodes import (
    get_all_nodes_and_filter,
    get_neighborhood,
    filter,
    sort,
    limit,
    take_intersection,
    take_union,
    take_difference,
)

################################################################

langchain.debug = False

################################################################
# TO BE REMOVED EVENTUALLY                                     #
################################################################


def format_nodeset(nodeset):
    # Restrict to maximum 10 results
    nodeset = nodeset[:10]

    # Convert list of nodes to list of strings
    results = [f"[{node['NodeType']}] {node['Title']} ({node['NodeKey']})" for node in nodeset]

    # Return a string with one line per node
    return '\n'.join(results)


def emojify(node_type):
    if node_type == 'Concept':
        return '⚛️'
    elif node_type == 'Person':
        return '👤'
    elif node_type == 'Course':
        return '📚'
    elif node_type == 'Lecture':
        return '📖'
    elif node_type == 'Unit':
        return '🔬'
    elif node_type == 'Publication':
        return '📄'
    else:
        return ''


def pluralise(node_type):
    if node_type == 'Person':
        return 'People'
    else:
        return f"{node_type}s"


def build_context_message_step(instructions, i):
    if i is None:
        return ''

    operator = instructions[i]['operator']
    params = instructions[i]['params']

    if operator == 'Search':
        [node_type, name] = params
        return f"the {emojify(node_type)} {node_type} \"{name}\""

    elif operator == 'All':
        [node_type, field, value] = params
        return f"all {emojify(node_type)} {pluralise(node_type)}, filtered by {field}={value}"

    elif operator == 'Neighborhood':
        [nodeset_name, node_type] = params

        j = find_instruction_index(instructions, nodeset_name)

        return f"{emojify(node_type)} {pluralise(node_type)} related to {build_context_message_step(instructions, j)}"

    elif operator == 'Filter':
        [nodeset_name, field, value] = params

        j = find_instruction_index(instructions, nodeset_name)

        return f"{build_context_message_step(instructions, j)}, filtered by {field}={value}"

    elif operator == 'FilterRange':
        [nodeset_name, field, min_value, max_value] = params

        j = find_instruction_index(instructions, nodeset_name)

        return f"{build_context_message_step(instructions, j)}, filtered by {field} between {min_value} and {max_value}"

    elif operator == 'Sort':
        [nodeset_name, field, order] = params

        j = find_instruction_index(instructions, nodeset_name)

        return f"{build_context_message_step(instructions, j)}, sorted by {field} ({order})"

    elif operator == 'Limit':
        [nodeset_name, n] = params

        j = find_instruction_index(instructions, nodeset_name)

        return f"at most {n} {build_context_message_step(instructions, j)}"

    elif operator == 'Intersection':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return f"the intersection of {build_context_message_step(instructions, left_j)} and {build_context_message_step(instructions, right_j)}"

    elif operator == 'Union':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return f"the union of {build_context_message_step(instructions, left_j)} and {build_context_message_step(instructions, right_j)}"

    elif operator == 'Difference':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return f"the nodes in {build_context_message_step(instructions, left_j)} not in {build_context_message_step(instructions, right_j)}"

    elif operator == 'Return':
        context_messages = []
        for nodeset_name in params:
            j = find_instruction_index(instructions, nodeset_name)
            context_message = f"Showing {build_context_message_step(instructions, j)}"
            context_messages.append(context_message)

        return context_messages

    return []


def build_context_message(instructions):
    return build_context_message_step(instructions, -1)


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
# INSTRUCTIONS                                                 #
################################################################


def parse_instructions(instructions):
    instructions = instructions.split('\n')

    parsed_instructions = []
    for instruction in instructions:
        if 'Return' in instruction:
            lhs = None
            rhs = instruction
        else:
            if '=' not in instruction:
                continue

            # Split LHS and RHS
            pieces = instruction.split('=')
            pieces = [piece.strip() for piece in pieces]
            [lhs, rhs] = pieces

        if '(' not in rhs or ')' not in rhs:
            continue

        # Get operator and arguments from RHS
        begin = rhs.find('(')
        end = rhs.find(')')
        operator = rhs[: begin]
        params = rhs[begin + 1: end].split(',')
        params = [param.strip() for param in params]

        parsed_instructions.append({'lhs': lhs, 'operator': operator, 'params': params})

    return parsed_instructions


def follow_instructions(instructions):
    nodesets = {}
    for instruction in instructions:
        lhs = instruction['lhs']
        operator = instruction['operator']
        params = instruction['params']

        if operator == 'Search':
            nodeset = search_nodes(*params)
            nodeset = nodeset[:1]
            nodesets[lhs] = nodeset

        elif operator == 'All':
            [node_type, field, value] = params
            nodesets[lhs] = get_all_nodes_and_filter(node_type, field, value)

        elif operator == 'Neighborhood':
            [nodeset_name, node_type] = params
            nodesets[lhs] = get_neighborhood(nodesets[nodeset_name], node_type)

        elif operator == 'Filter':
            [nodeset_name, field, value] = params
            nodesets[lhs] = filter(nodesets[nodeset_name], field, value)

        elif operator == 'FilterRange':
            [nodeset_name, field, min_value, max_value] = params
            nodesets[lhs] = filter(nodesets[nodeset_name], field, (min_value, max_value))

        elif operator == 'Sort':
            [nodeset_name, field, order] = params
            nodesets[lhs] = sort(nodesets[nodeset_name], field, order)

        elif operator == 'Limit':
            [nodeset_name, n] = params
            nodesets[lhs] = limit(nodesets[nodeset_name], int(n))

        elif operator == 'Intersection':
            [left_nodeset_name, right_nodeset_name] = params
            nodesets[lhs] = take_intersection(nodesets[left_nodeset_name], nodesets[right_nodeset_name])

        elif operator == 'Union':
            [left_nodeset_name, right_nodeset_name] = params
            nodesets[lhs] = take_union(nodesets[left_nodeset_name], nodesets[right_nodeset_name])

        elif operator == 'Difference':
            [left_nodeset_name, right_nodeset_name] = params
            nodesets[lhs] = take_difference(nodesets[left_nodeset_name], nodesets[right_nodeset_name])

        elif operator == 'Return':
            return [nodesets[nodeset_name] for nodeset_name in params]

    # Fallback: If no return operation, return nodeset referenced last
    nodeset = nodesets[lhs]

    return [nodeset]


def find_instruction_index(instructions, lhs):
    for i in range(len(instructions)):
        if instructions[i]['lhs'] == lhs:
            return i

    return None


def build_context(instructions, i=-1):
    if i is None:
        return {}

    operator = instructions[i]['operator']
    params = instructions[i]['params']

    if operator == 'Search':
        [node_type, name] = params
        return {'operation': 'search', 'node_type': node_type, 'name': name}

    elif operator == 'All':
        [node_type, field, value] = params
        return {'operation': 'all', 'node_type': node_type, 'field': field, 'value': value}

    elif operator == 'Neighborhood':
        [nodeset_name, node_type] = params

        j = find_instruction_index(instructions, nodeset_name)

        return {'operation': 'neighborhood', 'node_type': node_type, 'child': build_context(instructions, j)}

    elif operator == 'Filter':
        [nodeset_name, field, value] = params

        j = find_instruction_index(instructions, nodeset_name)

        return {'operation': 'filter', 'field': field, 'value': value, 'child': build_context(instructions, j)}

    elif operator == 'FilterRange':
        [nodeset_name, field, min_value, max_value] = params

        j = find_instruction_index(instructions, nodeset_name)

        return {'operation': 'filter_range', 'field': field, 'min_value': min_value, 'max_value': max_value, 'child': build_context(instructions, j)}

    elif operator == 'Sort':
        [nodeset_name, field, order] = params

        j = find_instruction_index(instructions, nodeset_name)

        return {'operation': 'sort', 'field': field, 'order': order, 'child': build_context(instructions, j)}

    elif operator == 'Limit':
        [nodeset_name, n] = params

        j = find_instruction_index(instructions, nodeset_name)

        return {'operation': 'limit', 'n': int(n), 'child': build_context(instructions, j)}

    elif operator == 'Intersection':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return {'operation': 'intersection', 'left_child': build_context(instructions, left_j), 'right_child': build_context(instructions, right_j)}

    elif operator == 'Union':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return {'operation': 'union', 'left_child': build_context(instructions, left_j), 'right_child': build_context(instructions, right_j)}

    elif operator == 'Difference':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return {'operation': 'difference', 'left_child': build_context(instructions, left_j), 'right_child': build_context(instructions, right_j)}

    elif operator == 'Return':
        contexts = []
        for nodeset_name in params:
            j = find_instruction_index(instructions, nodeset_name)
            contexts.append(build_context(instructions, j))

        return contexts

    return []


################################################################
# MAIN                                                         #
################################################################

def wrap_nlp(conversation_id, query, results):
    chain = get_chain('wrapper', conversation_id)

    llm_output = chain({'input': f"Query: {query}\nResults: {str(results)}"})

    return llm_output['text']


def conversation(conversation_id, text):
    chain = get_chain('instructions', conversation_id)

    # Run chain with human message
    llm_output = chain({'input': text})

    # Extract instructions as string
    instructions_str = llm_output['text']

    # with get_openai_callback() as cb:
    #     # Update token count in database for usage control
    #     token_count = cb.total_tokens
    #     update_token_count(user_id, token_count)

    print(text)
    print(instructions_str)

    # Parse instructions from text to list of dict
    try:
        instructions = parse_instructions(instructions_str)
    except Exception as e:
        traceback.print_exc()
        return [], 'error parsing instructions'

    # Follow instructions to get target nodeset as list of nodes
    try:
        nodesets = follow_instructions(instructions)
    except Exception as e:
        traceback.print_exc()
        return [], 'error following instructions'

    # Build context dictionaries and context messages based on instructions
    # (e.g. "showing People related to the Concept Urbanism")
    try:
        contexts = build_context(instructions)
        context_messages = build_context_message(instructions)

        if not isinstance(contexts, list):
            contexts = [contexts]

        if not isinstance(context_messages, list):
            context_messages = [context_messages]

    except Exception as e:
        traceback.print_exc()
        return [], 'error building context'

    return [
        {
            'nodeset': nodeset,
            'context': context,
            'context_message': context_message
        }
        for nodeset, context, context_message in zip(nodesets, contexts, context_messages)
    ], ''
