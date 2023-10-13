from app.interfaces.db import execute_query
from app.interfaces.es import get_nodeset, search_node_contents


def drop_duplicates(nodeset):
    unique_nodeset = []
    ids = []
    for node in nodeset:
        if node['NodeKey'] in ids:
            continue

        unique_nodeset.append(node)
        ids.append(node['NodeKey'])

    return unique_nodeset


def get_key_field(node_type, key):
    key_fields = {
        ('Person', 'Gender'): 'gender_en',
        ('Person', 'Sex'): 'gender_en',
        ('Course', 'ExamType'): 'exam_type',
        ('Course', 'SectionCode'): 'section_code',
        ('Course', 'Section'): 'section_code',
        ('Publication', 'Year'): 'year',
        ('Publication', 'Date'): 'year',
        ('Publication', 'PublicationType'): 'publication_type_en',
        ('Publication', 'Type'): 'publication_type_en',
        ('Publication', 'Journal'): 'published_in',
        ('Publication', 'Conference'): 'published_in',
        ('Lecture', 'Date'): 'creation_date_title',
    }

    if (node_type, key) in key_fields:
        return key_fields[node_type, key]

    return key


def get_key_value(node_type, key_field, value):
    if isinstance(value, tuple):
        return (
            get_key_value(node_type, key_field, value[0]),
            get_key_value(node_type, key_field, value[1])
        )

    key_values = {
        ('Person', 'gender_en', 'Woman'): 'Female',
        ('Person', 'gender_en', 'Man'): 'Male',
    }

    if (node_type, key_field, value) in key_values:
        return key_values[node_type, key_field, value]

    return value


def want_exact_match(node_type, key_field):
    want_exact_matches = [
        ('Person', 'gender_en'),
        ('Publication', 'year'),
    ]

    return (node_type, key_field) in want_exact_matches


def filter_node_ids(node_type, key, value, filter_ids=None):
    # Build table name
    table_name = f'Nodes_N_{node_type}'

    # Project implemented (node_type, key) to field name
    key_field = get_key_field(node_type, key)

    # Project implemented (node_type, key_field, value) to field value for enumerations
    key_value = get_key_value(node_type, key_field, value)

    # Filter all nodes table using the (key_field, key_value)
    query = f"""
        SELECT id
        FROM graphsearch.{table_name}
    """

    conditions = []
    if filter_ids is not None:
        conditions.append(f"""id IN ({', '.join(['%s'] * len(filter_ids))})""")

    if isinstance(value, tuple):
        conditions.append(f"""{key_field} >= "{key_value[0]}" """)
        conditions.append(f"""{key_field} <= "{key_value[1]}" """)
    elif want_exact_match(node_type, key_field):
        conditions.append(f"""{key_field} = "{key_value}" """)
    else:
        conditions.append(f"""{key_field} LIKE "%{key_value}%" """)

    conditions_str = '\nAND '.join(conditions)

    query += f"""WHERE {conditions_str}"""

    if filter_ids is None:
        results = execute_query(query)
    else:
        results = execute_query(query, filter_ids)

    node_ids = [str(r) for r, in results]

    return node_ids


################################################################


def get_all_nodes_and_filter(node_type, key, value):
    # Get node ids
    node_ids = filter_node_ids(node_type, key, value)

    # Get nodeset from ids
    nodeset = get_nodeset(node_ids, node_type)

    return nodeset


def get_neighborhood(nodeset, node_type):
    if len(nodeset) == 0:
        return []

    # Assuming all nodes in nodeset are of the same type
    source_node_type = nodeset[0]['NodeType']
    target_node_type = node_type

    # Build table name
    table_name = f'Edges_N_{source_node_type}_N_{target_node_type}'

    # Extract ids from nodeset
    ids = [node['NodeKey'] for node in nodeset]

    # Run query
    query = f"""
        SELECT to_id
        FROM graphsearch.{table_name}
        WHERE from_id IN ({', '.join(['%s'] * len(ids))})
        ORDER BY score DESC
    """
    results = execute_query(query, ids)
    neighbor_ids = [r for r, in results]

    # Remove duplicates while keeping order
    neighbor_ids = list(dict.fromkeys(neighbor_ids))

    # Get nodes from ids
    nodes = get_nodeset(neighbor_ids, target_node_type)
    nodes = drop_duplicates(nodes)

    return nodes


################################################################


def filter(nodeset, key, value):
    """
    Filters a nodeset according to a field's value or range.
    The key identifier is used to infer which field of the nodes database table is used.
    If no field can be inferred, the value is matched against the Content field on elasticsearch.

    Args:
      nodeset (list): A list of nodes.
      key (str): A loose identifier of the node field to be used for filtering.
      value (int|float|tuple): The value or interval to be used for filtering.

    Returns (list):
      A nodeset whose nodes are a subset of the original nodeset and satisfy the condition
      inferred through the key field.
    """

    if len(nodeset) == 0:
        return []

    # Assuming all nodes in nodeset are of the same type
    node_type = nodeset[0]['NodeType']

    # Extract ids from nodeset
    ids = [node['NodeKey'] for node in nodeset]

    try:
        filtered_ids = filter_node_ids(node_type, key, value, filter_ids=ids)
    except Exception as e:
        # If the above does not work as expected, just search both key and value on the Content field in elasticsearch
        nodeset = search_node_contents(value, node_type, filter_ids=ids)
        filtered_ids = [node['NodeKey'] for node in nodeset]

    # Filter nodeset, keep only ids found above
    filtered_nodeset = [node for node in nodeset if node['NodeKey'] in filtered_ids]

    return filtered_nodeset


def sort(nodeset, key, order):
    if len(nodeset) == 0:
        return []

    # Assuming all nodes in nodeset are of the same type
    node_type = nodeset[0]['NodeType']

    # Build table name
    table_name = f'Nodes_N_{node_type}'

    # Extract ids from nodeset
    ids = [node['NodeKey'] for node in nodeset]

    # Project implemented (node_type, key) to field name
    key_field = get_key_field(node_type, key)

    # Project order to database syntax
    if 'DESC' in order or 'Desc' in order or 'desc' in order:
        key_order = 'DESC'
    else:
        key_order = 'ASC'

    # Sort the node ids table using the (key_field, key_value)
    query = f"""
        SELECT id
        FROM graphsearch.{table_name}
        WHERE id IN ({', '.join(['%s'] * len(ids))})
        ORDER BY {key_field} {key_order}
    """

    results = execute_query(query, ids)
    sorted_ids = [str(r) for r, in results]

    # Filter nodeset, keep only ids found above
    filtered_nodeset = [node for node in nodeset if node['NodeKey'] in sorted_ids]

    # Sort nodeset according to returned order
    sorted_nodeset = sorted(filtered_nodeset, key=lambda node: sorted_ids.index(node['NodeKey']))

    return sorted_nodeset


def limit(nodeset, n):
    return nodeset[:n]


################################################################


def take_intersection(left_nodeset, right_nodeset):
    left_ids = {node['NodeKey'] for node in left_nodeset}
    right_ids = {node['NodeKey'] for node in right_nodeset}

    common_ids = left_ids & right_ids

    common_nodeset = [node for node in left_nodeset + right_nodeset if node['NodeKey'] in common_ids]
    common_nodeset = drop_duplicates(common_nodeset)

    return common_nodeset


def take_union(left_nodeset, right_nodeset):
    union_nodeset = drop_duplicates(left_nodeset + right_nodeset)

    return union_nodeset


def take_difference(left_nodeset, right_nodeset):
    right_ids = {node['NodeKey'] for node in right_nodeset}

    difference_nodeset = [node for node in left_nodeset if node['NodeKey'] not in right_ids]

    return difference_nodeset
