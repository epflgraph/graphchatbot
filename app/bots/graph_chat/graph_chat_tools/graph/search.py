from graphes.core.graphes import GraphES

from app.bots.graph_chat.graph_chat_tools.graph.clean import clean_nodes
from app.config import config


async def search_graph(query: str) -> list:
    """
    Search the EPFL knowledge graph for nodes matching the given `query`.
    """
    client = GraphES()

    nodes = client.search(query=query, index_name=config['elasticsearch']['index'], limit=5)
    nodes = clean_nodes(nodes)

    return nodes


if __name__ == '__main__':
    import asyncio

    nodes = asyncio.run(search_graph(query="Anna Fontcuberta"))

    print(nodes)
