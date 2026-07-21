import datetime

import httpx


async def search_news(query: str) -> list:
    """
    Search exercises from EPFL news website.
    """

    print("[NEWS TOOL]", f"Called the `search_news` tool with input `{query}`")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://search-backend.epfl.ch/api/cse",
            params={
                "hl": "en",
                "siteSearch": "actu.epfl.ch/news",
                "siteSearchFilter": "i",
                "q": query,
            },
        )
    items = response.json().get("items", [])
    print("[NEWS TOOL]", f"Got {len(items)} news articles")

    cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=3 * 365)).strftime("%Y-%m-%d")
    news = []
    for item in items:
        og_list = item.get("pagemap", {}).get("metatags", [])
        if not og_list:
            continue
        og_item = og_list[0]

        date = og_item.get("article:published_time", "")
        if date and date < cutoff_date:
            continue

        news.append(
            {
                "title": og_item.get("og:title", ""),
                "description": og_item.get("og:description", ""),
                "url": og_item.get("og:url", ""),
                "date": og_item.get("article:published_time", ""),
            }
        )

    return news
