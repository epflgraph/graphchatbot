"""
This module contains the organisational links coming from elasticsearch that are considered for each node type
"""

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
        'Lecture': {'field': 'lectures', 'limit': None},
    },
    'MOOC': {
        'Person': {'field': 'instructors', 'limit': None},
        'Lecture': {'field': 'lectures', 'limit': None},
    },
    'Category': {
        'Concept': {'field': 'concepts', 'limit': None}
    },
    'Concept': {
        'Category': {'field': 'category', 'limit': 1}
    },
    'Lecture': {
        'Course': {'field': 'courses', 'limit': None},
        'MOOC': {'field': 'MOOCs', 'limit': None},
    }
}


def get_organisational_field_details(source_node_type, target_node_type):
    try:
        return organisational_fields_mapping[source_node_type][target_node_type]
    except Exception as e:
        print('[WARNING]', f"No organisational fields defined for node types {source_node_type} and {target_node_type}")
        return {}


def get_organisational_field_names(node_type):
    if node_type in organisational_fields_mapping:
        return [row['field'] for row in organisational_fields_mapping[node_type].values()]

    return []
