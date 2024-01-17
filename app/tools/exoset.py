"""
This module contains the tool to search for exercises in EXOSET using its API.
"""

import multiprocessing
import requests

import pandas as pd

from app.nodes import search_node, get_neighborhood

API_URL = f"https://test-exoset.epfl.ch/graphapi"

cache = {}


def fetch_concept_exercises(node):
    exercises = requests.post(API_URL, params={'concept': node['Title']}).json()

    exercises = pd.DataFrame(exercises)
    exercises['coef'] = node['Score']

    return exercises


def fetch_all_exercises(nodeset):
    with multiprocessing.Pool() as pool:
        results = pool.map(fetch_concept_exercises, nodeset)

    return results


def search_exercises(concept: str) -> list:
    print("[EXOSET]", f"Called search EXOSET tool with input `{concept}`")

    # Max number of exercises to be returned
    n = 5

    # Check if result is cached
    if concept in cache:
        return cache[concept]

    # Get nodeset of one node with the first match
    nodeset = search_node('Concept', concept, n=50, return_scores=True, search_title=True)

    # Fallback: Search node Content instead of Title
    if len(nodeset) == 0:
        nodeset = search_node('Concept', concept, n=50, return_scores=True, search_title=False)

    print("[EXOSET]", f"Got {len(nodeset)} concepts to query for exercises")

    if len(nodeset) == 0:
        print("[EXOSET]", f"No exercises found, returning empty list")
        return []

    # Send requests in parallel to EXOSET's API to obtain exercises for every found concept.
    # We put them together in a DataFrame with their returned score and a coefficient,
    # which is the elasticsearch score of each matched concept.
    # This coefficient will be used to ponderate exercises,
    # so that exercises coming from worse matches see their score decreased.
    all_exercises = fetch_all_exercises(nodeset)
    all_exercises = pd.concat(all_exercises)

    # Return empty if no exercises found for any of the neighbours
    if len(all_exercises) == 0:
        return []

    # Keep only direct matches
    all_exercises = all_exercises[all_exercises['score'] >= 1]

    # We update the score by multiplying by the coefficient then group by exercise
    # (different concepts can return the same exercise so there can be repetitions)
    # and sort by descending final score.
    all_exercises['coef'] = all_exercises['coef'] / all_exercises['coef'].max()
    all_exercises['score'] = all_exercises['coef'] * all_exercises['score']
    all_exercises = all_exercises.groupby(by=['title', 'url']).aggregate(score=('score', 'sum')).reset_index()
    all_exercises = all_exercises.sort_values(by='score', ascending=False).reset_index(drop=True)

    # Return only the first n exercises to the LLM, otherwise we use a lot of tokens (+cost and +latency)
    # which are not going to be used in the LLM's final output anyway.
    all_exercises = all_exercises[:n]

    # Convert DataFrame to list
    all_exercises = all_exercises.to_dict(orient='records')

    # Store result in cache
    cache[concept] = all_exercises

    return all_exercises


def search_exercises_nbh(concept: str) -> list:
    # FIXME: Delete this, use search_exercises instead

    print("[EXOSET]", f"Called search EXOSET tool with input `{concept}`")

    # Check if result is cached
    if concept in cache:
        return cache[concept]

    # Get nodeset of one node with the first match
    nodeset = search_node('Concept', concept)

    if len(nodeset) == 0:
        return []

    # Get neighboring nodeset with edge scores
    neighboring_nodeset = get_neighborhood(nodeset, 'Concept', return_order=True)

    # Normalise scores: the first match (the node itself) gets a score of 1, the rest of scores are divided by the maximum + 1
    nodeset[0]['Order'] = 1

    if len(neighboring_nodeset) > 0:
        max_score = max([node['Order'] for node in neighboring_nodeset])
    else:
        max_score = 0

    for node in neighboring_nodeset:
        node['Order'] /= (max_score + 1)

    # Put together the found node with its neighbours
    full_nodeset = nodeset + neighboring_nodeset
    print("[EXOSET]", f"Got {len(full_nodeset)} concepts to query for exercises")

    # Send requests in parallel to EXOSET's API to obtain exercises for every found concept.
    # We put them together in a DataFrame with their returned score and a coefficient,
    # which is the edge score from the matched concept to each neighbour.
    # This coefficient will be used to ponderate exercises,
    # so that exercises coming from weak neighbors see their score decreased.
    all_exercises = fetch_all_exercises(full_nodeset)
    all_exercises = pd.concat(all_exercises)

    # Return empty if no exercises found for any of the neighbours
    if len(all_exercises) == 0:
        return []

    # We update the score by multiplying by the coefficient (edge score),
    # then group by exercise (different concepts can return the same exercise so there can be repetitions)
    # and sort by descending final score.
    all_exercises['score'] = all_exercises['coef'] * all_exercises['score']
    all_exercises = all_exercises.groupby(by=['title', 'url']).aggregate(score=('score', 'sum')).reset_index()
    all_exercises = all_exercises.sort_values(by='score', ascending=False).reset_index(drop=True)

    # Return only the first 10 exercises to the LLM, otherwise we use a lot of tokens (+cost and +latency)
    # which are not going to be used in the LLM's final output anyway.
    all_exercises = all_exercises[:10]

    # Convert DataFrame to list
    all_exercises = all_exercises.to_dict(orient='records')

    # Store result in cache
    cache[concept] = all_exercises

    return all_exercises

