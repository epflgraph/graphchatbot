import requests


def search_news(query: str) -> list:
    print("[NEWS]", f"Called search news tool with input `{query}`")

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
    print("[NEWS]", f"Got {len(items)} news articles")

    news = [
        {
            key: item[key]
            for key in ['title', 'link', 'snippet']
        }
        for item in items
    ]

    return news
