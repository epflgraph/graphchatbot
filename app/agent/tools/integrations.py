"""
This module contains the tool to run searches in the RAG integration indices in elasticsearch
"""

from typing import Optional, Annotated

from langgraph.prebuilt import InjectedState

from app.interfaces.graphai import GraphAIClient


def search_integration(state: Annotated[dict, InjectedState], query: str, limit: Optional[int] = 10) -> list:
    """
    Performs a search in a relevant document store. It returns up to `limit` document chunks.
    """

    integration = state['integration']

    print("[RAG TOOL]", f"Called the `search_integration` tool with integration=`{integration}` input=`{query}` and limit=`{limit}`")

    # Return empty if input is empty
    if not query:
        return []

    gac = GraphAIClient()

    # Prepare payload
    payload = {
        'index': integration,
        'text': query,
        # 'filters': {'lang': lang},
        'limit': limit
    }

    # TODO try with non-existent index make sure it works

    # Send request and return empty if it fails
    try:
        response = gac.call_sync_endpoint(endpoint='/rag/retrieve', payload=payload)
    except Exception as e:
        print("[RAG TOOL]", f"Error retrieving document chunks: {e}")
        return []

    # Return empty if response is not marked as successful
    if not response.get('successful'):
        print("[RAG TOOL]", f"Unsuccessful retrieval of chunks: {response.get('result', [])}")
        return []

    print("[RAG TOOL]", f"Retrieved {len(response.get('result', []))} document chunks.")

    return response.get('result', [])


if __name__ == '__main__':
    query = "EPFL parental leave policy"
    state = {'integration': 'lex'}

    results = search_integration(state=state, query=query, limit=10)
    print(results)
