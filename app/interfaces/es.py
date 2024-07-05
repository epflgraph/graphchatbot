"""
This module instantiates an elasticsearch interface under the name `es` and makes it available for import throughout the application.
"""

from elasticsearch_interface.es import ES

from app.config import config

es = ES(config['elasticsearch'], config['elasticsearch']['index'])


def search(text, node_type=None, limit=10, return_links=False, return_scores=False):
    ################################################################
    # Build filter clause                                          #
    ################################################################

    filter_clause = [
        {
            "terms": {"doc_institution.keyword": ["EPFL", "Ont"]}
        },
        # {
        #     "terms": {"links.link_institution.keyword": ["EPFL", "Ont"]}
        # }
    ]

    if isinstance(node_type, list):
        filter_clause.append(
            {
                "terms": {"doc_type.keyword": node_type}
            }
        )
    elif isinstance(node_type, str):
        filter_clause.append(
            {
                "term": {"doc_type.keyword": node_type}
            }
        )

    ################################################################
    # Build should clause                                          #
    ################################################################
    match_en_clause = {
        "multi_match": {
            "type": "most_fields",
            "operator": "and",
            # "fuzziness": "AUTO",
            "fields": [
                "name.en",
                "name.en.keyword",
                "name.en.raw",
                "name.en.trigram",
                "name.en.sayt._2gram",
                "name.en.sayt._3gram",
                "short_description.en",
                "long_description.en^0.001"
            ],
            "query": text
        }
    }

    match_fr_clause = {
        "multi_match": {
            "type": "most_fields",
            "operator": "and",
            # "fuzziness": "AUTO",
            "fields": [
                "name.fr",
                "name.fr.keyword",
                "name.fr.raw",
                "name.fr.trigram",
                "name.fr.sayt._2gram",
                "name.fr.sayt._3gram",
                "short_description.fr",
                "long_description.fr^0.001"
            ],
            "query": text
        }
    }

    match_en_fr_clause = {
        "dis_max": {
            "queries": [match_en_clause, match_fr_clause]
        }
    }

    match_id_clause = {
        "term": {
            "doc_id.keyword": {
                "boost": 10,
                "value": text
            }
        }
    }

    should_clause = [match_id_clause, match_en_fr_clause]

    ################################################################
    # Build query                                                  #
    ################################################################
    query = {
        "function_score": {
            "score_mode": "multiply",
            "functions": [{"field_value_factor": {"field": "degree_score"}}],
            "query": {
                "bool": {
                    "filter": filter_clause,
                    "should": should_clause,
                    "minimum_should_match": 1
                }
            }
        }
    }

    ################################################################
    # Build fields                                                 #
    ################################################################

    node_fields = ["doc_type", "doc_id", "name", "short_description", "links"]

    link_fields = ["link_type", "link_id", "link_name", "link_rank", "link_short_description"]

    type_specific_fields = {
        'course': ["latest_academic_year"],
        'lecture': ["video_duration"],
        'mooc': ["level", "domain", "language", "platform"],
        'person': ["gender", "is_at_epfl"],
        'publication': ["year", "publisher", "published_in"],
        'unit': ["is_research_unit", "is_active_unit"],
        'category': ["depth"],
        'concept': [],
        'startup': []
    }

    fields = node_fields + [type_field for _, type_fields in type_specific_fields.items() for type_field in type_fields]

    if return_links:
        fields += [f"links.{link_field}" for link_field in link_fields]
        fields += [f"links.{type_field}" for _, type_fields in type_specific_fields.items() for type_field in type_fields]

    ################################################################
    # Run search                                                   #
    ################################################################

    response = es.client.search(index=es.index, query=query, source_includes=fields, size=limit)
    hits = response['hits']['hits']
    if return_scores:
        hits = [{**hit['_source'], 'score': hit['_score']} for hit in hits]
    else:
        hits = [hit['_source'] for hit in hits]

    return hits


if __name__ == '__main__':
    nodes = search("green function", node_type='Lecture', limit=3, return_links=True, return_scores=False)
    print(nodes)
