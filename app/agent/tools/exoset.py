"""
This module contains the tool to search for exercises in EXOSET using its API.
"""

import multiprocessing
import requests

import pandas as pd

from elasticsearch_interface.es import ESGraphSearch

from app.config import config

API_URL = f"https://exoset.epfl.ch/graphapi"
TEST_API_URL = f"https://test-exoset.epfl.ch/graphapi"

cache = {}

# Set multiprocessing start method as 'spawn'. Currently, this is the default on MacOS, but 'fork' is the default on other POSIX systems,
# which leads to issues as it clashes with FastAPI/uvicorn. Starting child processes with 'fork' behaves as the OS fork operation,
# i.e. cloning the current process with the same memory state (e.g. variables), while starting them with 'spawn' creates a fresh python process
# with an empty memory space, which is slightly slower but avoids these issues.
# For more info check https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
try:
    multiprocessing.set_start_method('spawn')
except RuntimeError:
    pass


def fetch_concept_exercises(node):
    # Trying PROD API
    try:
        exercises = requests.post(API_URL, params={'concept': node['name']['en']}).json()
        exercises = pd.DataFrame(exercises)
        exercises['concept_id'] = node['doc_id']
        exercises['coef'] = node['score']

        return exercises
    except Exception:
        print("[EXOSET TOOL]", "The request to EXOSET PROD API failed. Trying EXOSET TEST API...")

    # Fallback to TEST API
    try:
        exercises = requests.post(TEST_API_URL, params={'concept': node['name']['en']}).json()
        exercises = pd.DataFrame(exercises)
        exercises['concept_id'] = node['doc_id']
        exercises['coef'] = node['score']

        return exercises
    except Exception:
        print("[EXOSET TOOL]", "The request to EXOSET TEST API failed. Returning no exercises.")

    # Everything failed, return empty
    return pd.DataFrame([])


def fetch_all_exercises(nodes):
    with multiprocessing.Pool() as pool:
        results = pool.map(fetch_concept_exercises, nodes)

    return results


async def search_exercises(query: str, language: str = 'EN') -> list:
    """
    Search exercises from EPFL's EXOSET database that best match the given `query`, which should be in English.
    The parameter `language` will prioritise exercises in that language, if available.
    """

    print("[EXOSET TOOL]", f"Called the `search_exercises` tool with input `{query}` and language `{language}`")

    # Standardise language parameter
    if language.lower() in ['fr', 'french', 'français']:
        language = 'FR'
    else:
        language = 'EN'

    # Check if result is cached
    if query in cache:
        print("[EXOSET TOOL]", f"Found {len(cache[query])} cached exercises for query `{query}` and language `{language}`, returning those")
        return cache[query]

    es = ESGraphSearch(config['elasticsearch'], config['elasticsearch']['index'])
    nodes = es.search(query, node_type='Concept', limit=50, return_links=False, return_scores=True)

    print("[EXOSET TOOL]", f"Got {len(nodes)} concepts to query for exercises: {[node['name']['en'] for node in nodes]}")

    if len(nodes) == 0:
        print("[EXOSET TOOL]", f"No concepts found, returning empty list")
        return []

    # Send requests in parallel to EXOSET's API to obtain exercises for every found concept.
    # We put them together in a DataFrame with their returned score and a coefficient,
    # which is the elasticsearch score of each matched concept.
    # This coefficient will be used to ponderate exercises,
    # so that exercises coming from worse matches see their score decreased.
    all_exercises = fetch_all_exercises(nodes)
    all_exercises = pd.concat(all_exercises)

    # Return empty if no exercises found for any of the neighbours
    if len(all_exercises) == 0:
        return []

    # Remove duplicates in the non-preferred languages when they exist
    all_exercises = pd.merge(
        all_exercises,
        all_exercises.groupby(by=['concept_id', 'author', 'series', 'exercise']).aggregate(count=('langue_file', 'count')).reset_index(),
        how='inner',
        on=['concept_id', 'author', 'series', 'exercise']
    )
    all_exercises = all_exercises[
        (all_exercises['count'] == 1)
        | (all_exercises['langue_file'] == language)
    ]

    # Compute the final score as (score + 2 * ontology_score) * coef
    # We double the ontology score as we deem it more important than the regular score
    all_exercises['coef'] = all_exercises['coef'] / all_exercises['coef'].max()
    all_exercises['score'] = (all_exercises['score'] + 2 * all_exercises['ontology_score']) * all_exercises['coef']

    # We group by exercise (different concepts can return the same exercise so there can be repetitions)
    # and sort by descending final score.
    all_exercises = all_exercises.groupby(by=['title', 'url']).aggregate(score=('score', 'sum')).reset_index()
    all_exercises = all_exercises.sort_values(by='score', ascending=False).reset_index(drop=True)

    print("[EXOSET TOOL]", f"Found {len(all_exercises)} exercises among all concepts")

    # Return only up to 20 exercises not to drown in tokens
    all_exercises = all_exercises[:20]

    # Convert DataFrame to list
    all_exercises = all_exercises.to_dict(orient='records')

    # Store result in cache
    print("[EXOSET TOOL]", f"Storing {len(all_exercises)} exercises for query `{query}` and language `{language}` in cache")
    cache[query] = all_exercises

    return all_exercises


if __name__ == '__main__':
    pd.set_option('display.max_rows', 400)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1000)

    print(search_exercises(query="derivatives", language='en'))
