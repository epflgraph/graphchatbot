"""
This module contains the tool to run searches in the RAG integration indices in elasticsearch
"""

from typing import Optional, Annotated

from langgraph.prebuilt import InjectedState

from app.interfaces.graphai import GraphAIClient


def search_integration(state: Annotated[dict, InjectedState], keywords: list, limit: Optional[int] = 10) -> list:
    """
    Performs a search in a relevant document store with the given `keywords`.
    """

    integration = state['integration']

    print("[RAG TOOL]", f"Called the `search_integration` tool with integration=`{integration}` keywords=`{keywords}` and limit=`{limit}`")

    # Clean keywords
    keywords = [k.strip() for k in keywords if k.strip()]

    # Return empty if no keywords
    if not keywords:
        return []

    gac = GraphAIClient()

    results = {}
    for k in keywords:
        # Prepare payload
        payload = {
            'index': integration,
            'text': k,
            # 'filters': {'lang': lang},
            'limit': limit,
        }

        # Send request and return empty if it fails
        try:
            response = gac.call_sync_endpoint(endpoint='/rag/retrieve', payload=payload)
        except Exception as e:
            print("[RAG TOOL]", f"Error retrieving document chunks: {e}")
            continue

        # Return empty if response is not marked as successful
        if not response.get('successful'):
            print("[RAG TOOL]", f"Unsuccessful retrieval of chunks: {response.get('result', [])}")
            continue

        # Store the results to aggregate them later
        i = 0
        for result in response.get('result', []):
            # Score increment is 1 (existence) plus a bonus between 0 and 1 (position)
            score_increment = 2 - i / (limit + 1)
            i += 1

            result_id = result.get('id')
            if not result_id:
                continue

            if result_id in results:
                results[result_id]['.score'] += score_increment
            else:
                results[result_id] = result
                result['.score'] = score_increment

    print("[RAG TOOL]", f"Retrieved {len(results)} document chunks.")

    # Sort the results in a list by descending score (which is an integer between 1 and n_keywords)
    results = sorted(results.values(), key=lambda result: result['.score'], reverse=True)

    # # Keep up to `limit` results
    # results = results[:limit]

    return results


if __name__ == '__main__':
    keywords = ["anna fontcuberta"]
    state = {'integration': 'servicedesk'}

    results = search_integration(state=state, keywords=keywords, limit=10)
    for result in results:
        print(result)
