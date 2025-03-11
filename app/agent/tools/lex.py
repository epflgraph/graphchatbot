"""
This module contains the tool to do RAG in the lex index.
"""

from typing import Optional, Literal

from app.interfaces.graphai import GraphAIClient


def search_lex(query: str, lang: Optional[Literal['en', 'fr']] = None, limit: Optional[int] = 10) -> list:
    """
    Performs a search in the current legal documents of EPFL about rules and regulations. It searches in the given `lang` (or in all languages if unspecified) and returns up to `limit` results.
    """

    print("[LEX TOOL]", f"Called the `search_lex` tool with input=`{query}`, lang=`{lang}` and limit=`{limit}`")

    # Return empty if input is empty
    if not query:
        return []

    gac = GraphAIClient()

    # Prepare payload
    payload = {
        'index': 'lex',
        'text': query,
        'lang': lang,
        'limit': limit
    }

    # Send request and return empty if it fails
    try:
        response = gac.call_sync_endpoint(endpoint='/rag/retrieve', payload=payload)
    except Exception as e:
        print("[LEX TOOL]", f"Error retrieving lex document chunks: {e}")
        return []

    # Return empty if response is not marked as successful
    if not response.get('successful'):
        print("[LEX TOOL]", f"Unsuccessful retrieval of lex chunks: {response.get('result', [])}")
        return []

    return response.get('result', [])


if __name__ == '__main__':
    print(search_lex(query="days of holidays", lang='fr'))
