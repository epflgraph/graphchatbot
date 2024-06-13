from app.interfaces.es import search

from app.config import config

################################################################
# Helper functions                                             #
################################################################


def clean_link(link):
    link = {
        'type': link['link_type'],
        'id': link['link_id'],
        'name_en': link['link_name']['en'],
        'name_fr': link['link_name']['fr'],
        # 'short_description': link['short_description']['en'],
        'ranking': link['link_rank'],
        'url': f"{config['graphsearch']['base_url']}/{link['link_type'].lower()}/{link['link_id']}"
    }

    return link


def clean_links(links, node_type):
    if node_type is None:
        return [clean_link(link) for link in links if link['link_rank'] <= 3]
    else:
        if isinstance(node_type, str):
            node_type = [node_type]
        return [clean_link(link) for link in links if link['link_rank'] <= 10 and link['link_type'] in node_type]


def clean_node(node, node_type):
    node = {
        'type': node['doc_type'],
        'id': node['doc_id'],
        'name_en': node['name']['en'],
        'name_fr': node['name']['fr'],
        'short_description': node['short_description']['en'],
        'url': f"{config['graphsearch']['base_url']}/{node['doc_type'].lower()}/{node['doc_id']}",
        'links': clean_links(node['links'], node_type)
    }

    return node


def clean_nodes(nodes, node_type):
    return [clean_node(node, node_type) for node in nodes]


################################################################
# Tool function                                                #
################################################################


def search_nodes(query: str, node_type: list | str = None) -> list:
    """
    Search nodes from the EPFL Graph that best match the given `query` and return them along with their related nodes of the given `node_type`.
    """

    print('[GRAPH]', f"Called `search_graph` tool with query=`{query}` and node_type=`{node_type}`")

    # Search nodes matching the given query
    nodes = search(query, node_type=None, limit=3, return_links=True, return_scores=False)
    print('[GRAPH]', f"Got {len(nodes)} nodes from elasticsearch with {[len(node['links']) for node in nodes]} links")

    # Build a nodes object by renaming, cleaning and filtering some fields
    nodes = clean_nodes(nodes, node_type)
    print('[GRAPH]', f"Kept {len(nodes)} nodes after cleanup with {[len(node['links']) for node in nodes]} links")

    return nodes


if __name__ == '__main__':
    search_nodes("machine learning", node_type=['People', 'Publication'])
