import re
from datetime import timedelta

import pandas as pd

from app.interfaces.es import search
from app.interfaces.db import db_manager

from app.config import config


################################################################
# Cleaner functions                                            #
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
# Timestamp functions                                          #
################################################################

def get_timestamp_pairs(nodes):
    # Crawl the nodes and store the pairs (concept/category, lecture for which we need the timestamps)
    pairs = []
    for node in nodes:
        if node['type'] in ['Concept', 'Category']:
            for link in node['links']:
                if link['type'] == 'Lecture':
                    pairs.append((node['type'], node['id'], link['id']))
        elif node['type'] == 'Lecture':
            for link in node['links']:
                if link['type'] in ['Concept', 'Category']:
                    pairs.append((link['type'], link['id'], node['id']))

    return pairs


def get_timestamps(pairs):
    columns = ['node_type', 'node_id', 'lecture_id', 'timestamp_s']

    if not pairs:
        return pd.DataFrame(columns=columns)

    table = 'graph_lectures.Data_N_Object_N_Object_T_CalculatedFields'
    fields = ['to_object_type', 'to_object_id', 'from_object_id', 'field_value']
    conditions = {
        'from_institution_id': 'EPFL',
        'from_object_type': 'Lecture',
        'to_institution_id': 'Ont',
        'field_name': 'primary_timestamp',
        '(to_object_type, to_object_id, from_object_id)': pairs,
    }
    timestamps = pd.DataFrame(db_manager.db.find(table_name=table, fields=fields, conditions=conditions), columns=columns)

    return timestamps


def update_with_timestamps(nodes, timestamps, top_concept_or_category):
    # Iterate over nodes to add timestamp field and update the url
    for node in nodes:
        if node['type'] in ['Concept', 'Category']:
            for link in node['links']:
                if link['type'] == 'Lecture':
                    try:
                        timestamp_sec = timestamps.loc[
                            (timestamps['node_type'] == node['type'])
                            & (timestamps['node_id'] == node['id'])
                            & (timestamps['lecture_id'] == link['id']),
                            'timestamp_s',
                        ].iloc[0]
                        timestamp_sec = int(timestamp_sec)
                        td = timedelta(seconds=timestamp_sec)
                        link[f"best_timestamp_for_{to_snake_case(node['name_en'])}"] = str(td)
                        link['url'] += f'?t={timestamp_sec}'
                    except (IndexError, TypeError):
                        pass
        elif node['type'] == 'Lecture':
            if top_concept_or_category is None:
                continue

            top_type = top_concept_or_category['doc_type']
            top_id = top_concept_or_category['doc_id']
            if (top_type, top_id) in [(link['type'], link['id']) for link in node['links']]:
                try:
                    timestamp_sec = timestamps.loc[
                        (timestamps['node_type'] == top_type)
                        & (timestamps['node_id'] == top_id)
                        & (timestamps['lecture_id'] == node['id']),
                        'timestamp_s',
                    ].iloc[0]
                    timestamp_sec = int(timestamp_sec)
                    td = timedelta(seconds=timestamp_sec)
                    top_name = top_concept_or_category['name']['en']
                    node[f"best_timestamp_for_{to_snake_case(top_name)}"] = str(td)
                    node['url'] += f'?t={timestamp_sec}'
                except (IndexError, TypeError):
                    pass

    return nodes


def to_snake_case(s):
    # Replace all non-word characters (everything except numbers and letters) with '_'
    s = re.sub(r'[^\w\s]', ' ', s)
    # Remove leading and trailing spaces
    s = s.strip()
    # Replace all spaces with '_'
    s = re.sub(r'\s+', '_', s)
    # Make lowercase
    s = s.lower()
    return s


def add_lecture_timestamps(nodes, top_concept_or_category):
    # Extract the concept/category - lecture pairs from the nodes
    pairs = get_timestamp_pairs(nodes)

    # Return if no pairs
    if not pairs:
        return nodes

    # Fetch timestamps from the database
    timestamps = get_timestamps(pairs)

    # Add the timestamp information to the appropriate nodes and links
    nodes = update_with_timestamps(nodes, timestamps, top_concept_or_category)

    return nodes

################################################################
# Tool function                                                #
################################################################


def search_nodes(query: str, node_type: list | str = None) -> list:
    """
    Search nodes from the EPFL Graph that best match the given `query` and return them along with their related nodes of the given `node_type`.
    A list of nodes is returned. Aside from its own fields, each node has a `links` field which in turn contains a list of the node's related nodes.
    """

    print('[NODES TOOL]', f"Called `search_nodes` tool with query=`{query}` and node_type=`{node_type}`")

    # Search nodes matching the given query
    nodes = search(query, node_type=None, limit=3, return_links=True, return_scores=False)
    print('[NODES TOOL]', f"Got nodes ({[(node['name']['en'], node['doc_id']) for node in nodes]}) from elasticsearch with {[len(node['links']) for node in nodes]} links")

    # Build a nodes object by renaming, cleaning and filtering some fields
    nodes = clean_nodes(nodes, node_type)
    print('[NODES TOOL]', f"Kept {len(nodes)} nodes after cleanup with {[len(node['links']) for node in nodes]} links")

    # Add timestamps to lectures wherever needed
    # For that, we need the top matching concept or person, in case there are Lecture-Concept or Lecture-Category edges in the results
    top_concept_or_category = search(query, node_type=['Concept', 'Category'], limit=1, return_links=False, return_scores=False)
    if top_concept_or_category:
        [top_concept_or_category] = top_concept_or_category
    else:
        top_concept_or_category = None
    nodes = add_lecture_timestamps(nodes, top_concept_or_category)

    return nodes


if __name__ == '__main__':
    nodes = search_nodes("steepest descent", node_type=['Lecture', 'Course'])
    print(nodes)
