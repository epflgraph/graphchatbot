"""
This module contains cleaner functions that rearrange and filter node lists from elasticsearch to make them suitable for the LLM
"""

from app.bots.graph_chat.graph_chat_tools.graph.organisational_links import get_organisational_field_details
from app.config import config


def clean_link(link):
    link = {
        "type": link.get("link_type", ""),
        "id": link.get("link_id", ""),
        "name_en": link.get("link_name", {}).get("en", ""),
        "name_fr": link.get("link_name", {}).get("fr", ""),
        "short_description_en": link.get("link_short_description", {}).get("en", ""),
        "short_description_fr": link.get("link_short_description", {}).get("fr", ""),
        "url": f"{config['graphsearch']['base_url']}/{link.get('link_type', '').lower()}/{link.get('link_id', '')}",
    }

    return link


def clean_links(links, node_types):
    # Split node links between semantic and organisational
    semantic_links = [link for link in links if link.get("link_subtype", "") == "Semantic"]
    organisational_links = [link for link in links if link.get("link_subtype", "") != "Semantic"]

    # Clean all the organisational ones
    organisational_links = [clean_link(link) for link in organisational_links]

    # Define node_types properly and how many links of a given node_type we may have
    if node_types is None:
        node_types = [link.get("link_type", "") for link in semantic_links]
        node_types = list(
            dict.fromkeys(node_types)
        )  # Remove duplicates. This is like list(set(x)) but preserving the order.
        limit = 5
    else:
        if isinstance(node_types, str):
            node_types = [node_types]
        limit = 10

    # Clean up semantic links and keep only links of the given node types, and up to the defined limit
    clean_semantic_links = []
    for node_type in node_types:
        node_type_semantic_links = [link for link in semantic_links if link.get("link_type", "") == node_type]
        clean_semantic_links += [clean_link(link) for link in node_type_semantic_links[:limit]]

    return organisational_links, clean_semantic_links


def clean_node(node, node_types):
    # Clean node links and separate into organisational vs. semantic
    organisational_links, semantic_links = clean_links(node.get("links", []), node_types)

    organisational_fields = {}
    for link in organisational_links:
        organisational_field_details = get_organisational_field_details(node.get("doc_type", ""), link.get("type", ""))

        if not organisational_field_details:
            continue

        field = organisational_field_details["field"]
        limit = organisational_field_details["limit"]

        if field in organisational_fields:
            if limit is None or len(organisational_fields[field]) < limit:
                organisational_fields[field].append(link)
        else:
            if limit == 1:
                organisational_fields[field] = link
            else:
                organisational_fields[field] = [link]

    node = {
        "type": node.get("doc_type", ""),
        "id": node.get("doc_id", ""),
        "name_en": node.get("name", {}).get("en", ""),
        "name_fr": node.get("name", {}).get("fr", ""),
        "short_description_en": node.get("short_description", {}).get("en", ""),
        "short_description_fr": node.get("short_description", {}).get("fr", ""),
        "url": f"{config['graphsearch']['base_url']}/{node.get('doc_type', '').lower()}/{node.get('doc_id', '')}",
        **organisational_fields,
        "nearest_nodes": semantic_links,
    }

    return node


def clean_nodes(nodes, node_types=None):
    return [clean_node(node, node_types) for node in nodes]
