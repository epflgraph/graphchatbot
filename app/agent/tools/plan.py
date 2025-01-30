"""
This module contains the tool to search in plan.epfl.ch.
"""

import urllib.parse


def search_plan(query: str) -> dict:
    """
    Performs a search in the website of the EPFL plan. Returns the most relevant result for the given query.
    """

    print("[PLAN TOOL]", f"Called search plan tool with input `{query}`")

    # Encode url (to avoid spaces and symbols in the url)
    query = urllib.parse.quote(query)

    return {'url': f'https://plan.epfl.ch/?q={query}'}


if __name__ == '__main__':
    print(search_plan("Patrick Jermann"))
