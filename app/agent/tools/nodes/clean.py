"""
This module contains cleaner functions that rearrange and filter node lists from elasticsearch to make them suitable for the LLM
"""

from app.config import config

from app.agent.tools.nodes.organisational_links import get_organisational_field_details


def clean_link(link):
    link = {
        'type': link['link_type'],
        'id': link['link_id'],
        'name_en': link['link_name']['en'],
        'name_fr': link['link_name']['fr'],
        'short_description': link['link_short_description']['en'],
        'url': f"{config['graphsearch']['base_url']}/{link['link_type'].lower()}/{link['link_id']}"
    }

    return link


def clean_links(links, node_types):
    # Split node links between semantic and organisational
    semantic_links = [link for link in links if link['link_subtype'] == 'Semantic']
    organisational_links = [link for link in links if link['link_subtype'] != 'Semantic']

    # Clean all the organisational ones
    organisational_links = [clean_link(link) for link in organisational_links]

    # Define node_types properly and how many links of a given node_type we may have
    if node_types is None:
        node_types = list(set(link['link_type'] for link in semantic_links))
        limit = 5
    else:
        if isinstance(node_types, str):
            node_types = [node_types]
        limit = 10

    # Clean up semantic links and keep only links of the given node types, and up to the defined limit
    clean_semantic_links = []
    for node_type in node_types:
        node_type_semantic_links = [link for link in semantic_links if link['link_type'] == node_type]
        clean_semantic_links += [clean_link(link) for link in node_type_semantic_links[:limit]]

    return organisational_links, clean_semantic_links


def clean_node(node, node_types):
    # Clean node links and separate into organisational vs. semantic
    organisational_links, semantic_links = clean_links(node['links'], node_types)

    organisational_fields = {}
    for link in organisational_links:
        organisational_field_details = get_organisational_field_details(node['doc_type'], link['type'])

        field = organisational_field_details['field']
        limit = organisational_field_details['limit']

        if field in organisational_fields:
            if limit is None or len(organisational_fields[field]) < limit:
                organisational_fields[field].append(link)
        else:
            if limit == 1:
                organisational_fields[field] = link
            else:
                organisational_fields[field] = [link]

    node = {
        'type': node['doc_type'],
        'id': node['doc_id'],
        'name_en': node['name']['en'],
        'name_fr': node['name']['fr'],
        'short_description': node['short_description']['en'],
        'url': f"{config['graphsearch']['base_url']}/{node['doc_type'].lower()}/{node['doc_id']}",
        **organisational_fields,
        'nearest_nodes': semantic_links,
    }

    return node


def clean_nodes(nodes, node_types):
    return [clean_node(node, node_types) for node in nodes]
