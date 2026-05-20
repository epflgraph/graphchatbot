"""
This module contains functions that fetch timestamps for lecture suggestions in lists of nodes
"""

import re
from datetime import timedelta

import pandas as pd

from app.agent.tools.nodes.organisational_links import get_organisational_field_names
from app.auth.db import _execute


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
        placeholders = ', '.join(['%s'] * len(pairs))
        rows = _execute(
            f"""
            SELECT to_object_type, to_object_id, from_object_id, field_value
            FROM graph_lectures.Data_N_Object_N_Object_T_CalculatedFields
            WHERE from_institution_id = %s
              AND from_object_type = %s
              AND to_institution_id = %s
              AND field_name = %s
              AND (to_object_type, to_object_id, from_object_id) IN ({placeholders})
            """,
            values=['EPFL', 'Lecture', 'Ont', 'primary_timestamp'] + pairs,
        )
        timestamps = pd.DataFrame(rows, columns=columns)
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
