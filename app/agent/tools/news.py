"""
This module contains the tool to search for news in actu.epfl.ch.
"""

import requests


def search_news(query: str) -> list:
    """
    Search exercises from EPFL news website.
    """

    print("[NEWS TOOL]", f"Called search news tool with input `{query}`")

    endpoint_base_url = "https://search-backend.epfl.ch/api/cse"
    path_params = {
        'hl': 'en',
        'siteSearch': 'actu.epfl.ch/news',
        'siteSearchFilter': 'i',
        'q': query,
    }
    path_params_str = '&'.join([f'{k}={v}' for k, v in path_params.items()])

    endpoint_full_url = f'{endpoint_base_url}?{path_params_str}'

    response = requests.get(endpoint_full_url).json()
    items = response.get('items', [])
    print("[NEWS TOOL]", f"Got {len(items)} news articles")

    news = [
        {
            target_key: item[source_key]
            for source_key, target_key in [('title', 'title'), ('link', 'url'), ('snippet', 'snippet')]
        }
        for item in items
    ]

    return news


if __name__ == '__main__':
    print(search_news("Anna Fontcuberta"))
