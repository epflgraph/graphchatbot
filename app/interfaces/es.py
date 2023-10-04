from elasticsearch import Elasticsearch

from app.config import config

es = Elasticsearch(
    [config['elasticsearch']['host']],
    http_auth=(config['elasticsearch']['user'], config['elasticsearch']['password']),
    ca_certs=config['elasticsearch']['cert'],
)


def get_nodes(ids, node_type):
    """Returns nodes based on exact match on the NodeKey field."""

    # Keep only first 1000 ids to avoid elasticsearch issues
    ids = ids[:1000]

    query = {
        "bool": {
            "filter": [
                {"term": {"NodeType.keyword": node_type}},
                {"terms": {"NodeKey.keyword": ids}}
            ]
        }
    }

    sort = [{"DegreeScore": {"order": "desc"}}]

    res = es.search(index='graph_full_piper', source=['NodeKey', 'NodeType', 'Title'], query=query, sort=sort, size=1000)
    results = [hit['_source'] for hit in res['hits']['hits']]

    return results


def search_nodes(text, node_type):
    """Returns nodes based on a full-text match on the Title field."""
    query = {
        "function_score": {
            "score_mode": "multiply",
            "functions": [
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
            ],
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
                                "type": "bool_prefix",
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
            "functions": [
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
            ],
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
