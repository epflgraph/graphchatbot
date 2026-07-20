import asyncio
import logging

import httpx
import pandas as pd
from graphes.core.graphes import GraphES

from app.config import config

logger = logging.getLogger(__name__)

API_URL = "https://exoset.epfl.ch/graphapi"
TEST_API_URL = "https://test-exoset.epfl.ch/graphapi"

_exoset_cache = {}


async def _fetch_concept_exercises(client: httpx.AsyncClient, node: dict) -> pd.DataFrame:
    try:
        response = await client.post(API_URL, params={"concept": node["name"]["en"]})
        exercises = pd.DataFrame(response.json())
        exercises["concept_id"] = node["doc_id"]
        exercises["coef"] = node["score"]
        return exercises
    except Exception:
        logger.info("[EXOSET TOOL] The request to EXOSET PROD API failed. Trying EXOSET TEST API...")

    try:
        response = await client.post(TEST_API_URL, params={"concept": node["name"]["en"]})
        exercises = pd.DataFrame(response.json())
        exercises["concept_id"] = node["doc_id"]
        exercises["coef"] = node["score"]
        return exercises
    except Exception:
        logger.info("[EXOSET TOOL] The request to EXOSET TEST API failed. Returning no exercises.")

    return pd.DataFrame([])


async def search_exoset(query: str, language: str = "EN") -> list:
    """
    Search exercises from EPFL's EXOSET database that best match the given `query`, which should be in English.
    The parameter `language` will prioritise exercises in that language, if available.
    """

    # TODO Migrate this to use graphregistry rather than exoset API

    logger.info("[EXOSET TOOL] Called the `search_exercises` tool with input `%s` and language `%s`", query, language)

    if language.lower() in ["fr", "french", "français"]:
        language = "FR"
    else:
        language = "EN"

    if query in _exoset_cache:
        logger.info(
            "[EXOSET TOOL] Found %d cached exercises for query `%s` and language `%s`, returning those",
            len(_exoset_cache[query]),
            query,
            language,
        )
        return _exoset_cache[query]

    client = GraphES()
    nodes = await asyncio.to_thread(
        client.search,
        query=query,
        node_types=["Concept"],
        index_name=config["elasticsearch"]["index"],
        limit=50,
    )

    logger.info(
        "[EXOSET TOOL] Got %d concepts to query for exercises: %s", len(nodes), [node["name"]["en"] for node in nodes]
    )

    if len(nodes) == 0:
        logger.info("[EXOSET TOOL] No concepts found, returning empty list")
        return []

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[_fetch_concept_exercises(client, node) for node in nodes])
    all_exercises = pd.concat(results)

    if len(all_exercises) == 0:
        return []

    all_exercises = pd.merge(
        all_exercises,
        all_exercises.groupby(by=["concept_id", "author", "series", "exercise"])
        .aggregate(count=("langue_file", "count"))
        .reset_index(),
        how="inner",
        on=["concept_id", "author", "series", "exercise"],
    )
    all_exercises = all_exercises[(all_exercises["count"] == 1) | (all_exercises["langue_file"] == language)]

    all_exercises["coef"] = all_exercises["coef"] / all_exercises["coef"].max()
    all_exercises["score"] = (all_exercises["score"] + 2 * all_exercises["ontology_score"]) * all_exercises["coef"]

    all_exercises = all_exercises.groupby(by=["title", "url"]).aggregate(score=("score", "sum")).reset_index()
    all_exercises = all_exercises.sort_values(by="score", ascending=False).reset_index(drop=True)

    logger.info("[EXOSET TOOL] Found %d exercises among all concepts", len(all_exercises))

    all_exercises = all_exercises[:20]
    all_exercises = all_exercises.to_dict(orient="records")

    logger.info(
        "[EXOSET TOOL] Storing %d exercises for query `%s` and language `%s` in cache",
        len(all_exercises),
        query,
        language,
    )
    _exoset_cache[query] = all_exercises

    return all_exercises


if __name__ == "__main__":
    exos = asyncio.run(search_exoset("double pendulum"))

    print(exos)
