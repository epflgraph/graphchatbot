"""
This module instantiates an elasticsearch interface under the name `es` and makes it available for import throughout the application.
"""

from elasticsearch_interface.es import ES

from app.config import config

es = ES(config['elasticsearch'], config['elasticsearch']['index'])


def search(texts, node_type=None, limit=10, return_links=False, return_scores=False):
    # Make texts always a list
    if isinstance(texts, str):
        texts = [texts]

    ################################################################
    # Build text match clauses                                     #
    ################################################################

    def build_fields(lang):
        return [
            f"name.{lang}",
            f"name.{lang}.keyword",
            f"name.{lang}.raw",
            f"name.{lang}.trigram",
            f"name.{lang}.sayt._2gram",
            f"name.{lang}.sayt._3gram",
            f"short_description.{lang}",
            f"long_description.{lang}^0.001"
        ]

    en_clauses = []
    fr_clauses = []
    id_clauses = []
    for text in texts:
        en_clauses.append({
            "multi_match": {
                "fields": build_fields('en'),
                "query": text
            }
        })

        fr_clauses.append({
            "multi_match": {
                "fields": build_fields('fr'),
                "query": text
            }
        })

        id_clauses.append({
            "term": {
                "doc_id.keyword": {
                    "boost": 10,
                    "value": text
                }
            }
        })

    # en_query is an OR between matches against en fields for all texts
    en_query = {
        "bool": {
            "should": en_clauses,
            "minimum_should_match": 1
        }
    }

    # fr_query is an OR between matches against fr fields for all texts
    fr_query = {
        "bool": {
            "should": fr_clauses,
            "minimum_should_match": 1
        }
    }

    # We then take the maximum between the two (otherwise words spelled the same in both languages would be boosted)
    max_en_fr_query = {
        "dis_max": {
            "queries": [en_query, fr_query]
        }
    }

    ################################################################
    # Build filter clause                                          #
    ################################################################

    # We use only documents from EPFL or the ontology
    filter_clause = [
        {
            "terms": {"doc_institution.keyword": ["EPFL", "Ont"]}
        },
        # {
        #     "terms": {"links.link_institution.keyword": ["EPFL", "Ont"]}
        # }
    ]

    # And if node_types are specified, we keep only those documents
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
    # Build final query                                            #
    ################################################################

    # The final query does the following
    #   1. Keeps only documents satisfying the filter
    #   2. Looks at text matches in en and fr, and also exact matches against the id field.
    #   3. Updates match score multiplying by degree score
    query = {
        "function_score": {
            "score_mode": "multiply",
            "functions": [{"field_value_factor": {"field": "degree_score"}}],
            "query": {
                "bool": {
                    "filter": filter_clause,
                    "should": id_clauses + [max_en_fr_query],
                    "minimum_should_match": 1
                }
            }
        }
    }

    ################################################################
    # Build fields                                                 #
    ################################################################

    node_fields = ["doc_type", "doc_id", "name", "short_description"]

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
        fields += ['links']
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
    nodes = search(["Hausdorff Dimension", "Fractal Geometry", "Koch Snowflake"], node_type=None, limit=3, return_links=True, return_scores=False)
    print(nodes)
