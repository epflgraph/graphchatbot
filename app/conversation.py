from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

from app.interfaces.es import search_nodes
from app.nodes import get_neighborhood, take_intersection, take_union

from app.config import config

################################################################

system_message = """
    You are an assistant that translates natural language to queries on knowledge graphs.
    There are seven node types: `Concept`, `Person`, `Course`, `Unit`, `MOOC`, `Lecture` and `Publication`.
    Nodes have a `NodeKey`, a `NodeType` and a `Title`.
    
    For each query, you should return the sequence of instructions to produce the requested node set.
    The available instructions are the following:
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
    
    Do not use any other instruction or node type different from the ones above. Do not output any other text.
    
    For example, if the input is `people working on sustainability`, you should answer
    ```
    A = Node(Sustainability, Concept)
    B = Neighborhood(A, Person)
    ```
    
    Another example, if the input is `courses about solar cells and urbanism`, you should answer
    ```
    A = Node(Solar cells, Concept)
    B = Neighborhood(A, Course)
    C = Node(Urbanism, Concept)
    D = Neighborhood(C, Course)
    E = Intersection(B, D)
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
"""

################################################################

chat = ChatOpenAI(temperature=0, openai_api_key=config['openai']['api_key'])
memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
prompt = ChatPromptTemplate(
    messages=[
        SystemMessagePromptTemplate.from_template(system_message),
        MessagesPlaceholder(variable_name='chat_history'),
        HumanMessagePromptTemplate.from_template("{human_input}")
    ]
)

chain = LLMChain(
    llm=chat,
    prompt=prompt,
    verbose=False,
    memory=memory,
)

################################################################


def follow_instructions(instructions):
    instructions = instructions.split('\n')

    nodesets = {}
    for instruction in instructions:
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


def conversation(human_input):
    llm_output = chain({'human_input': human_input})

    # Extract instructions as string
    instructions = llm_output['text']

    print(human_input)
    print(instructions)

    try:
        # Follow instructions to get target nodeset as list of nodes
        nodeset = follow_instructions(instructions)

        # Convert nodeset into text
        text_nodeset = format_nodeset(nodeset)

        return text_nodeset
    except Exception:
        return instructions
