from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.callbacks import get_openai_callback
import langchain

from app.interfaces.es import search_nodes
from app.interfaces.db import update_token_count
from app.nodes import get_neighborhood, take_intersection, take_union, limit, filter

from app.config import config

langchain.debug = False

################################################################

system_message = """
    You are an assistant that translates natural language to queries on the knowledge graph of EPFL.
    There are six node types: `Concept`, `Person`, `Course`, `Unit`, `MOOC` and `Publication`.
    Nodes have a `NodeKey`, a `NodeType` and a `Title`.
    
    For each query, you should return the sequence of instructions to produce the requested node set.
    The available instructions always produce a nodeset, and they are the following:
    * Find a node by type and title:
    ```
    Node(<title>, <node_type>)
    ```
    * Get the neighborhood of a given type of a node set:
    ```
    Neighborhood(<nodeset>, <node_type>)
    ```
    * Intersect two nodesets:
    ```
    Intersection(<nodeset_1>, <nodeset_2>)
    ```
    * Take the union of two nodesets:
    ```
    Union(<nodeset_1>, <nodeset_2>)
    ```
    * Keep the first `n` nodes in a nodeset:
    ```
    Limit(<nodeset>, <n>)
    ```
    * Filter nodeset based on a field's value
    ```
    Filter(<nodeset>, <field>, <value>)
    ```
    
    Intersections and unions must are restricted to nodesets of the same type.
    Filters should be sensible and depend on the node type.
    Do not use any other instruction or node type different from the ones above.
    Do use exactly one of these instructions per line.
    Do not output any other text.
    
    For example, if the input is `labs that do research in data science`, you should answer
    ```
    A = Node(Data Science, Concept)
    B = Neighborhood(A, Unit)
    ```
    
    Another example, if the input is `three people working on sustainability`, you should answer
    ```
    A = Node(Sustainability, Concept)
    B = Neighborhood(A, Person)
    C = Limit(B, 3)
    ```
    
    Another example, if the input is `courses about solar cells and urbanism`, you should answer
    ```
    A = Node(Solar cells, Concept)
    B = Neighborhood(A, Course)
    C = Node(Urbanism, Concept)
    D = Neighborhood(C, Course)
    E = Intersection(B, D)
    ```
    
    Another example, if the input is `female experts in genomics`, you should answer
    ```
    A = Node(Genomics, Concept)
    B = Neighborhood(A, Person)
    C = Filter(B, Gender, Female)
    ```
    
    Yet another example, if the input is `people working in computer science who teach courses about physics`, you should answer
    ```
    A = Node(Computer Science, Concept)
    B = Neighborhood(A, Person)
    C = Node(Physics, Concept)
    D = Neighborhood(C, Course)
    E = Neighborhood(D, Person)
    F = Intersection(B, E)
    ```
    
    On subsequent requests always provide the complete list of instructions.
    For instance, if the input is `who is the teacher of the course MATH-302?`, you should answer
    ```
    A = Node(MATH-302, Course)
    B = Neighborhood(A, Person)
    ```
    If the user replies `does he teach any MOOCs?`, you should answer
    ```
    A = Node(MATH-302, Course)
    B = Neighborhood(A, Person)
    C = Neighborhood(B, MOOC)
    ```
    Then if the user replies `Is any of those about machine learning?`, you should answer
    ```
    A = Node(MATH-302, Course)
    B = Neighborhood(A, Person)
    C = Neighborhood(B, MOOC)
    D = Node(Machine Learning, Concept)
    E = Neighborhood(D, MOOC)
    F = Intersection(C, E)
    ```
"""

################################################################


def create_chain(memory_key):
    chat = ChatOpenAI(
        temperature=0,
        openai_api_key=config['openai']['api_key'],
    )
    memory = ConversationBufferMemory(memory_key=memory_key, return_messages=True)
    prompt = ChatPromptTemplate(
        messages=[
            SystemMessagePromptTemplate.from_template(system_message),
            MessagesPlaceholder(variable_name=memory_key),
            HumanMessagePromptTemplate.from_template("{human_input}")
        ]
    )

    return LLMChain(
        llm=chat,
        prompt=prompt,
        verbose=False,
        memory=memory,
    )


# Initialise object to store all chains
chains = {}

################################################################


def parse_instructions(instructions):
    instructions = instructions.split('\n')

    parsed_instructions = []
    for instruction in instructions:
        if '=' not in instruction:
            continue

        if '(' not in instruction or ')' not in instruction:
            continue

        # Split LHS and RHS
        pieces = instruction.split('=')
        pieces = [piece.strip() for piece in pieces]
        [lhs, rhs] = pieces

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

        if operator == 'Node':
            nodeset = search_nodes(*params)
            if len(nodeset) > 0:
                nodeset = [nodeset[0]]
            print(nodeset)
            nodesets[lhs] = nodeset

        elif operator == 'Neighborhood':
            [nodeset, node_type] = params
            nodesets[lhs] = get_neighborhood(nodesets[nodeset], node_type)

        elif operator == 'Intersection':
            [left_nodeset, right_nodeset] = params
            nodesets[lhs] = take_intersection(nodesets[left_nodeset], nodesets[right_nodeset])

        elif operator == 'Union':
            [left_nodeset, right_nodeset] = params
            nodesets[lhs] = take_union(nodesets[left_nodeset], nodesets[right_nodeset])

        elif operator == 'Limit':
            [nodeset, n] = params
            nodesets[lhs] = limit(nodesets[nodeset], int(n))

        elif operator == 'Filter':
            [nodeset, field, value] = params
            nodesets[lhs] = filter(nodesets[nodeset], field, value)

    # Take nodeset referenced last
    nodeset = nodesets[lhs]

    return nodeset


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
        return '📖'
    elif node_type == 'Unit':
        return '🔬'
    elif node_type == 'Publication':
        return '📄'
    elif node_type == 'MOOC':
        return '🎥'
    else:
        return ''


def pluralise(node_type):
    if node_type == 'Person':
        return 'People'
    else:
        return f"{node_type}s"


def find_instruction_index(instructions, lhs):
    for i in range(len(instructions)):
        if instructions[i]['lhs'] == lhs:
            return i

    return None


def build_context_message_step(instructions, i):
    if i is None:
        return ''

    operator = instructions[i]['operator']
    params = instructions[i]['params']

    if operator == 'Node':
        [name, node_type] = params
        return f"the {emojify(node_type)} {node_type} \"{name}\""

    elif operator == 'Neighborhood':
        [nodeset_name, node_type] = params

        j = find_instruction_index(instructions, nodeset_name)

        return f"{emojify(node_type)} {pluralise(node_type)} related to {build_context_message_step(instructions, j)}"

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

    elif operator == 'Limit':
        [nodeset_name, n] = params

        j = find_instruction_index(instructions, nodeset_name)

        return f"at most {n} {build_context_message_step(instructions, j)}"

    elif operator == 'Filter':
        [nodeset_name, field, value] = params

        j = find_instruction_index(instructions, nodeset_name)

        return f"{build_context_message_step(instructions, j)}, filtered by {field}={value}"

    return ''


def build_context_message(instructions):
    return f"Showing {build_context_message_step(instructions, -1)}"


def build_context_dict(instructions, i=-1):
    if i is None:
        return {}

    operator = instructions[i]['operator']
    params = instructions[i]['params']

    if operator == 'Node':
        [name, node_type] = params
        return {'operation': 'node', 'node_type': node_type, 'name': name}

    elif operator == 'Neighborhood':
        [nodeset_name, node_type] = params

        j = find_instruction_index(instructions, nodeset_name)

        return {'operation': 'neighborhood', 'node_type': node_type, 'child': build_context_dict(instructions, j)}

    elif operator == 'Intersection':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return {'operation': 'intersection', 'left_child': build_context_dict(instructions, left_j), 'right_child': build_context_dict(instructions, right_j)}

    elif operator == 'Union':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return {'operation': 'union', 'left_child': build_context_dict(instructions, left_j), 'right_child': build_context_dict(instructions, right_j)}

    elif operator == 'Limit':
        [nodeset_name, n] = params

        j = find_instruction_index(instructions, nodeset_name)

        return {'operation': 'limit', 'n': int(n), 'child': build_context_dict(instructions, j)}

    elif operator == 'Filter':
        [nodeset_name, field, value] = params

        j = find_instruction_index(instructions, nodeset_name)

        return {'operation': 'filter', 'field': field, 'value': value, 'child': build_context_dict(instructions, j)}

    return {}


def conversation(human_input):
    user_id = 1

    with get_openai_callback() as cb:
        # Create chain if it does not exist
        memory_key = 'chat_history'
        if memory_key not in chains:
            chains[memory_key] = create_chain(memory_key)

        # Run chain with human message
        llm_output = chains[memory_key]({'human_input': human_input})

        # Update token count in database for usage control
        token_count = cb.total_tokens
        update_token_count(user_id, token_count)

    # Extract instructions as string
    instructions_str = llm_output['text']

    print(human_input)
    print(instructions_str)

    try:
        # Parse instructions from text to list of dict
        instructions = parse_instructions(instructions_str)

        # Follow instructions to get target nodeset as list of nodes
        nodeset = follow_instructions(instructions)

        # Convert nodeset into text
        text_nodeset = format_nodeset(nodeset)

        # Build context message based on instructions (e.g. "showing People related to the Concept Urbanism")
        context_message = build_context_message(instructions)

        # Build context dictionary based on instructions
        context_dict = build_context_dict(instructions)
        print("Context message:", context_message)
        print("Context dict:", context_dict)

        return text_nodeset, context_message, context_dict
    except Exception as e:
        print('ERROR:', e)
        return instructions_str, '', {}
