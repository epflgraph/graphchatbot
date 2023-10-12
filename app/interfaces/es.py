from elasticsearch import Elasticsearch

from app.config import config

es = Elasticsearch(
    [config['elasticsearch']['host']],
    basic_auth=(config['elasticsearch']['user'], config['elasticsearch']['password']),
    ca_certs=config['elasticsearch']['cert'],
)

score_functions = [
    {
        "field_value_factor": {"field": "DegreeScore"}
    },
    {
        "filter": {"term": {"NodeType.keyword": "Concept"}},
        "weight": 512
    },
    {
        "filter": {"term": {"NodeType.keyword": "Person"}},
        "weight": 128
    },
    {
        "filter": {"term": {"NodeType.keyword": "Course"}},
        "weight": 128
    },
    {
        "filter": {"term": {"NodeType.keyword": "Unit"}},
        "weight": 64
    },
    {
        "filter": {"term": {"NodeType.keyword": "MOOC"}},
        "weight": 64
    },
    {
        "filter": {"term": {"NodeType.keyword": "Publication"}},
        "weight": 1
    }
]


def get_nodeset(ids, node_type):
    """Returns nodes based on exact match on the NodeKey field."""
    split_size = 1000

    # Split in two if too many ids
    n = len(ids)
    if n > split_size:
        first_nodeset = get_nodeset(ids[: n // 2], node_type)
        last_nodeset = get_nodeset(ids[n // 2:], node_type)
        return first_nodeset + last_nodeset

    # Fetch nodes from elasticsearch with the given ids
    query = {
        "bool": {
            "filter": [
                {"term": {"NodeType.keyword": node_type}},
                {"terms": {"NodeKey.keyword": ids}}
            ]
        }
    }

    res = es.search(index='graph_full_piper', source=['NodeKey', 'NodeType', 'Title'], query=query, size=split_size)
    nodeset = [hit['_source'] for hit in res['hits']['hits']]

    # Keep original order
    nodeset = sorted(nodeset, key=lambda node: ids.index(node['NodeKey']))

    return nodeset


def search_nodes(node_type, text):
    """Returns nodes based on a full-text match on the Title field."""
    query = {
        "function_score": {
            "score_mode": "multiply",
            "functions": score_functions,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "term": {"NodeType.keyword": node_type}
                        }
                    ],
                    "must": [
                        {
                            "multi_match": {
                                "type": "most_fields",
                                "operator": "and",
                                "fields": ["NodeKey", "Title", "Title.raw", "Title.trigram"],
                                "query": text
                            }
                        }
                    ]
                }
            }
        }
    }

    res = es.search(index='graph_full_piper', source=['NodeKey', 'NodeType', 'Title'], query=query)
    results = [hit['_source'] for hit in res['hits']['hits']]

    return results


def search_node_contents(text, node_type, filter_ids=None):
    """Returns nodes based on a full-text match on the Content field."""

    query = {
        "function_score": {
            "score_mode": "multiply",
            "functions": score_functions,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "term": {"NodeType.keyword": node_type}
                        }
                    ],
                    "must": [
                        {
                            "match": {
                                "Content": text
                            }
                        }
                    ]
                }
            }
        }
    }

    if filter_ids is not None:
        query['function_score']['query']['bool']['filter'].append({"terms": {"NodeKey.keyword": filter_ids}})

    res = es.search(index='graph_full_piper', source=['NodeKey', 'NodeType', 'Title'], query=query)

    # Return only results with a score higher than half of max_score
    results = [hit['_source'] for hit in res['hits']['hits'] if hit['_score'] > 0.5 * res['hits']['max_score']]

    return results
