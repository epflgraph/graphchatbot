from app.interfaces.db import execute_query
from app.interfaces.es import get_nodes


def drop_duplicates(nodeset):
    unique_nodeset = []
    ids = []
    for node in nodeset:
        if node['NodeKey'] in ids:
            continue

        unique_nodeset.append(node)
        ids.append(node['NodeKey'])

    return unique_nodeset


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


def get_neighborhood(nodeset, node_type):
    if len(nodeset) == 0:
        return []

    # Assuming all nodes in nodeset are of the same type
    source_node_type = nodeset[0]['NodeType']
    target_node_type = node_type

    # Dictionaries with information to build query
    id_fields = {
        'Concept': 'PageID',
        'Person': 'SCIPER',
        'Course': 'CourseCode',
        'Unit': 'UnitID',
        'MOOC': 'MoocID',
        'Publication': 'PublicationID'
    }

    table_names = {
        ('Concept', 'Concept'): 'Edges_N_Concept_N_Concept_T_GraphScore',
        ('Concept', 'Course'): 'Edges_N_Course_N_Concept_T_Semiauto',
        ('Concept', 'Person'): 'Edges_N_Person_N_Concept_T_Research',
        ('Concept', 'Publication'): 'Edges_N_Publication_N_Concept_T_AutoNLP',
        ('Concept', 'Unit'): 'Edges_N_Unit_N_Concept_T_Research',
        ('Person', 'Course'): 'Edges_N_Person_N_Course_T_StudyPlanTeacher',
        ('Person', 'Publication'): 'Edges_N_Person_N_Publication',
        ('Person', 'Unit'): 'Edges_N_Person_N_Unit',
        ('Person', 'MOOC'): 'Edges_N_Person_N_MOOC_T_Teaching'
    }

    # Build field names and table name
    source_id_field = id_fields[source_node_type]
    target_id_field = id_fields[target_node_type]

    table_name = table_names.get((source_node_type, target_node_type), '')
    if not table_name:
        table_name = table_names.get((target_node_type, source_node_type), '')

    # Extract ids from nodeset
    ids = [node['NodeKey'] for node in nodeset]

    query = f"""
    SELECT {target_id_field}
    FROM graph.{table_name}
    WHERE {source_id_field} IN ({', '.join(['%s'] * len(ids))})
    """

    results = execute_query(query, ids)
    neighbor_ids = [r for r, in results]

    # Remove duplicates while keeping order
    neighbor_ids = list(dict.fromkeys(neighbor_ids))

    # Get nodes from ids
    nodes = get_nodes(neighbor_ids, target_node_type)
    nodes = drop_duplicates(nodes)

    return nodes


def limit(nodeset, n):
    return nodeset[:n]


def filter(nodeset, key, value):
    if len(nodeset) == 0:
        return []

    # Assuming all nodes in nodeset are of the same type
    node_type = nodeset[0]['NodeType']

    # Extract ids from nodeset
    ids = [node['NodeKey'] for node in nodeset]

    # Dictionaries with information to build query
    id_fields = {
        'Concept': 'PageID',
        'Person': 'SCIPER',
        'Course': 'CourseCode',
        'Unit': 'UnitID',
        'MOOC': 'MoocID',
        'Publication': 'PublicationID'
    }

    table_names = {
        'Concept': 'Nodes_N_Concept',
        'Person': 'Nodes_N_Person',
        'Course': 'Nodes_N_Course',
        'Unit': 'Nodes_N_Unit',
        'MOOC': 'Nodes_N_MOOC',
        'Publication': 'Nodes_N_Publication'
    }

    key_fields = {
        ('Person', 'Gender'): 'Gender',
        ('Person', 'Sex'): 'Gender',
        ('Course', 'ExamType'): 'ExamType',
        ('Course', 'Credits'): 'Credits',
        ('Course', 'SectionCode'): 'SectionCode',
        ('Course', 'Section'): 'SectionCode',
        ('Unit', 'DateCreated'): 'UnitCreated',
        ('Unit', 'DateTerminated'): 'UnitTerminated',
        ('Unit', 'PrimaryLanguage'): 'PrimaryLanguage',
        ('Unit', 'Language'): 'PrimaryLanguage',
        ('Unit', 'IsEPFL'): 'IsEPFLUnit',
        ('Publication', 'Year'): 'Year',
        ('Publication', 'PublicationType'): 'PublicationType',
        ('Publication', 'Type'): 'PublicationType',
    }

    # Implemented node_type and key combinations
    id_field = id_fields[node_type]
    table_name = table_names[node_type]
    key_field = key_fields[node_type, key]

    query = f"""
    SELECT {id_field}
    FROM graph.{table_name}
    WHERE {id_field} IN ({', '.join(['%s'] * len(ids))})
    AND {key_field} = "{value}"
    """

    results = execute_query(query, ids)
    filtered_ids = [str(r) for r, in results]

    filtered_nodeset = [node for node in nodeset if node['NodeKey'] in filtered_ids]

    return filtered_nodeset

    # TODO: If key is not implemented, as a fallback mechanism, just lookup key and/or value on elasticsearch's Content field
