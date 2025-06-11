"""
This module contains the function to search nodes in the elasticsearch cluster based on some query and node types
"""

from app.agent.tools.nodes.clean import (
    clean_nodes,
)

from app.agent.tools.nodes.timestamps import (
    add_lecture_timestamps,
)

from elasticsearch_interface.es import ESGraphSearch

from app.config import config


def get_allowed_node_types(node_types: list | str):
    # Allow every source node type if no particular target node type is requested
    if node_types is None:
        return None

    # Mapping of allowed source node types depending on the given target node type
    allowed_node_types_mapping = {
        'Category': ['Category', 'Concept', 'Lecture'],
        'Concept': ['Category', 'Concept', 'Lecture'],
        'Lecture': ['Category', 'Concept', 'Lecture', 'Course', 'MOOC'],
        'Course': ['Category', 'Concept', 'Lecture', 'Course'],
        'MOOC': ['Category', 'Concept', 'Lecture', 'MOOC'],
        'Person': ['Category', 'Concept', 'Course', 'MOOC', 'Person'],
        'Publication': ['Category', 'Concept', 'Person', 'Publication', 'Unit'],
        'Unit': ['Category', 'Concept', 'Person', 'Publication', 'Unit'],
        'Startup': ['Category', 'Concept', 'Person', 'Startup'],
    }

    # Force node_types to be a list
    if isinstance(node_types, str):
        node_types = [node_types]

    # Put in the same list all allowed node types together
    allowed_node_types = []
    for node_type in node_types:
        allowed_node_types.extend(allowed_node_types_mapping[node_type])

    # Make them unique
    allowed_node_types = list(set(allowed_node_types))

    return allowed_node_types


def search_nodes(keywords: list[str] = None, node_type: list[str] | str = None) -> list:
    """
    Search nodes from the EPFL Graph that best match the given `keywords` and return them along with their related nodes of the given `node_type`.
    A list of nodes is returned. Each node can have some organisational fields (e.g. `instructors` of a Course or `authors` of a Publication) which contain a node or list of nodes.
    In addition, each node has a `nearest_nodes` field which contains a list of nodes that are semantically related to it (e.g. lectures about some Concept or people with the same research interests).
    """

    print('[NODES TOOL]', f"Called the `search_nodes` tool with keywords=`{keywords}` and node_type=`{node_type}`")

    if keywords is None:
        return []

    # Search nodes matching the given keywords:
    # We match not only nodes of the given node types, but some more.
    # For instance, we want `lectures about X` to match X against lectures but also concepts.
    allowed_node_types = get_allowed_node_types(node_type)

    # We override the behavior above because of the Osterwalder example
    allowed_node_types = None

    es = ESGraphSearch(config['elasticsearch'], config['elasticsearch']['index'])
    nodes = es.search(keywords, node_type=allowed_node_types, limit=3, return_links=True, return_scores=False)
    print('[NODES TOOL]', f"Got nodes ({[(node['doc_type'], node['doc_id'], node['name']['en']) for node in nodes]}) with {[len(node['links']) for node in nodes]} links from elasticsearch")

    # Build a nodes object by renaming, cleaning and filtering some fields
    nodes = clean_nodes(nodes, allowed_node_types)
    print('[NODES TOOL]', f"Kept nodes ({[(node['type'], node['id'], node['name_en']) for node in nodes]}) with {[len(node['nearest_nodes']) for node in nodes]} nearest nodes after cleanup")

    # # Add timestamps to lectures wherever needed
    # # For that, we need the top matching concept or person, in case there are Lecture-Concept or Lecture-Category edges in the results
    # top_concept_or_category = search(keywords, node_type=['Concept', 'Category'], limit=1, return_links=False, return_scores=False)
    # if top_concept_or_category:
    #     [top_concept_or_category] = top_concept_or_category
    # else:
    #     top_concept_or_category = None
    # nodes = add_lecture_timestamps(nodes, top_concept_or_category)

    return nodes


if __name__ == '__main__':
    nodes = search_nodes(keywords=["Anna Fontcuberta"], node_type='Person')
    print(nodes)
