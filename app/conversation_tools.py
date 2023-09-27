import langchain

from langchain.chat_models import ChatOpenAI

from langchain.agents import tool, OpenAIFunctionsAgent, AgentExecutor
from langchain.schema import SystemMessage

from app.interfaces.es import search_nodes
from app.nodes import get_neighborhood, take_intersection, take_union

from app.config import config

################################################################


@tool
def search_node_tool(name: str, node_type: str) -> dict:
    """Searches a node by name and node type. Returns a dictionary representing a node of the specified type and whose name is the closest to the given name."""

    results = search_nodes(name, node_type)

    if len(results) == 0:
        return []

    return [results[0]]


@tool
def get_neighborhood_tool(nodeset: list, node_type: str) -> list:
    """Returns the neighboring nodes of a given nodeset which are of the given node type. Both the given nodeset and the return object are lists of nodes."""
    neighbor_nodeset = get_neighborhood(nodeset, node_type)

    # Filter to avoid sending thousands of nodes to the LLM
    neighbor_nodeset = neighbor_nodeset[:10]

    return neighbor_nodeset


@tool
def take_intersection_tool(left_nodeset: list, right_nodeset: list):
    """Returns the intersection of the two given nodesets."""

    return take_intersection(left_nodeset, right_nodeset)


@tool
def take_union_tool(left_nodeset: list, right_nodeset: list):
    """Returns the union of the two given nodesets."""

    return take_union(left_nodeset, right_nodeset)


tools = [search_node_tool, get_neighborhood_tool, take_intersection_tool, take_union_tool]

################################################################

langchain.debug = False

# Create chat llm
chat = ChatOpenAI(temperature=0, openai_api_key=config['openai']['api_key'])

# Create prompt
system_message = """
    You are an assistant that answers questions by navigating a knowledge graph called EPFLGraph.
    There are the following node types: `Concept`, `Person`, `Course`, `Unit`, `MOOC`, `Lecture` and `Publication`.
    Nodes are represented by a dictionary with the keys `NodeKey`, `NodeType` and `Title`.
"""
prompt = OpenAIFunctionsAgent.create_prompt(system_message=SystemMessage(content=system_message))

# Create agent and agent executor
agent = OpenAIFunctionsAgent(llm=chat, tools=tools, prompt=prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, debug=True)


def conversation(human_input):
    output = agent_executor.run(human_input)

    return output
