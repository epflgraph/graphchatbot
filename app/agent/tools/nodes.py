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


# Dictionary that maps node and link types to the field name and the allowed limit of such links
organisational_fields_mapping = {
    'Unit': {
        'Unit': {'field': 'parent_unit', 'limit': 1},
        'Person': {'field': 'members', 'limit': None},
    },
    'Person': {
        'Unit': {'field': 'unit', 'limit': 1},
        'Publication': {'field': 'publications', 'limit': None},
        'Course': {'field': 'teaching_courses', 'limit': None},
        'MOOC': {'field': 'teaching_moocs', 'limit': None},
    },
    'Publication': {
        'Person': {'field': 'authors', 'limit': None},
    },
    'Course': {
        'Person': {'field': 'instructors', 'limit': None},
    },
    'MOOC': {
        'Person': {'field': 'instructors', 'limit': None},
    }
}


def get_organisational_field_names(node_type):
    if node_type in organisational_fields_mapping:
        return [row['field'] for row in organisational_fields_mapping[node_type].values()]

    return []


def clean_node(node, node_types):
    # Clean node links and separate into organisational vs. semantic
    organisational_links, semantic_links = clean_links(node['links'], node_types)

    organisational_fields = {}
    for link in organisational_links:
        field = organisational_fields_mapping[node['doc_type']][link['type']]['field']
        limit = organisational_fields_mapping[node['doc_type']][link['type']]['limit']

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


################################################################
# Timestamp functions                                          #
################################################################

def get_timestamp_pairs(nodes, top_concept_or_category):
    # Keep track of lecture ids, so we can later add pairs with the top concept or category
    lecture_ids = []

    # Crawl the nodes and store the pairs (concept/category, lecture for which we need the timestamps)
    pairs = []
    for node in nodes:
        if node['type'] in ['Concept', 'Category']:
            organisational_field_names = get_organisational_field_names(node['type'])
            for field in organisational_field_names + ['nearest_nodes']:
                for link in node.get(field, []):
                    if link['type'] == 'Lecture':
                        lecture_ids.append(node['id'])
                        pairs.append((node['type'], node['id'], link['id']))
        elif node['type'] == 'Lecture':
            organisational_field_names = get_organisational_field_names(node['type'])
            for field in organisational_field_names + ['nearest_nodes']:
                lecture_ids.append(node['id'])
                for link in node.get(field, []):
                    if link['type'] in ['Concept', 'Category']:
                        pairs.append((link['type'], link['id'], node['id']))

    # Add pairs of all seen lectures with the top concept or category
    if top_concept_or_category is not None:
        top_concept_or_category_type = top_concept_or_category['doc_type']
        top_concept_or_category_id = top_concept_or_category['doc_id']

        for lecture_id in lecture_ids:
            pairs.append((top_concept_or_category_type, top_concept_or_category_id, lecture_id))

    return pairs


def get_timestamps(pairs):
    columns = ['node_type', 'node_id', 'lecture_id', 'timestamp_s']

    if not pairs:
        return pd.DataFrame(columns=columns)

    try:
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
    except Exception as e:
        print("Cannot connect to table `graph_lectures.Data_N_Object_N_Object_T_CalculatedFields` to find timestamps, returning no timestamps.")
        print(e)
        return pd.DataFrame(columns=columns)

    return timestamps


def update_with_timestamps(nodes, timestamps, top_concept_or_category):
    # Iterate over nodes to add timestamp field and update the url
    for node in nodes:
        if node['type'] in ['Concept', 'Category']:
            organisational_field_names = get_organisational_field_names(node['type'])
            for field in organisational_field_names + ['nearest_nodes']:
                for link in node.get(field, []):
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

                            if node['type'] == 'Concept':
                                link['url'] += f"&concept_id={node['id']}"
                            elif node['type'] == 'Category':
                                link['url'] += f"&category_id={node['id']}"

                        except (IndexError, TypeError):
                            pass
        elif node['type'] == 'Lecture':
            if top_concept_or_category is None:
                continue

            try:
                top_type = top_concept_or_category['doc_type']
                top_id = top_concept_or_category['doc_id']
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

                if top_type == 'Concept':
                    node['url'] += f"&concept_id={top_id}"
                elif top_type == 'Category':
                    node['url'] += f"&category_id={top_id}"

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
    pairs = get_timestamp_pairs(nodes, top_concept_or_category)

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


def search_nodes(query: str, node_type: list | str = None) -> list:
    """
    Search nodes from the EPFL Graph that best match the given `query` and return them along with their related nodes of the given `node_type`.
    A list of nodes is returned. Each node can have some organisational fields (e.g. `instructors` of a Course or `authors` of a Publication) which contain a node or list of nodes.
    In addition, each node has a `nearest_nodes` field which contains a list of nodes that are semantically related to it (e.g. lectures about some Concept or people with the same research interests).
    """

    print('[NODES TOOL]', f"Called `search_nodes` tool with query=`{query}` and node_type=`{node_type}`")

    # Search nodes matching the given query:
    # We match not only nodes of the given node types, but some more.
    # For instance, we want `lectures about X` to match X against lectures but also concepts.
    allowed_node_types = get_allowed_node_types(node_type)
    nodes = search(query, node_type=allowed_node_types, limit=3, return_links=True, return_scores=False)
    print('[NODES TOOL]', f"Got nodes ({[(node['doc_type'], node['doc_id'], node['name']['en']) for node in nodes]}) with {[len(node['links']) for node in nodes]} links from elasticsearch")

    # Build a nodes object by renaming, cleaning and filtering some fields
    nodes = clean_nodes(nodes, allowed_node_types)
    print('[NODES TOOL]', f"Kept nodes ({[(node['type'], node['id'], node['name_en']) for node in nodes]}) with {[len(node['nearest_nodes']) for node in nodes]} nearest nodes after cleanup")

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
    nodes = search_nodes("MATH-211", node_type="Course")
    print(nodes)
