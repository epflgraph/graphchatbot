import requests

import pandas as pd

from app.nodes import search_node, get_neighborhood


def search_exercises(concept: str) -> list:
    print("[EXOSET]", f"Called search EXOSET tool with input `{concept}`")

    # Get nodeset of one node with the first match
    nodeset = search_node('Concept', concept)

    if len(nodeset) == 0:
        return []

    # Get neighboring nodeset with edge scores
    neighboring_nodeset = get_neighborhood(nodeset, 'Concept', return_order=True)

    # Normalise scores: the first match gets a score of 1, the rest of scores are divided by the maximum + 1
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

    # Iterate and send requests to EXOSET's API to obtain exercises for every found concept.
    # We put them together in a DataFrame with their returned score and a coefficient,
    # which is the edge score from the matched concept to each neighbour.
    # This coefficient will be used to ponderate exercises,
    # so that exercises coming from weak neighbors see their score decreased.
    import random
    random.seed(0)

    all_exercises = pd.DataFrame()
    for node in full_nodeset:
        url = f"https://exoset.epfl.ch/api/search?concept={node['Title']}"
        # result = requests.get(url).json()
        result = [
            {'title': "Spring Oscillator", 'link': "https://exoset.epfl.ch/resources/spring-oscillator", 'score': random.uniform(1.3, 1.8)},
            {'title': "Coupled oscillator", 'link': "https://exoset.epfl.ch/resources/coupled-oscillator", 'score': random.uniform(0.5, 1)},
            {'title': "Pendulum and spring system", 'link': "https://exoset.epfl.ch/resources/pendulum-and-spring-systemU42P", 'score': random.uniform(0.2, 0.7)},
        ]   # TODO: remove these placeholders when the API is available and work with the actual results

        node_exercises = pd.DataFrame(result)
        node_exercises['coef'] = node['Order']

        all_exercises = pd.concat([all_exercises, node_exercises])

    # We update the score by multiplying by the coefficient (edge score),
    # then group by exercise (different concepts can return the same exercise so there can be repetitions)
    # and sort by descending final score.
    all_exercises['score'] = all_exercises['coef'] * all_exercises['score']
    all_exercises = all_exercises.groupby(by=['title', 'link']).aggregate(score=('score', 'sum')).reset_index()
    all_exercises = all_exercises.sort_values(by='score', ascending=False)

    # Return only the first 10 exercises to the LLM, otherwise we use a lot of tokens (+cost and +latency)
    # which are not going to be used in the LLM's final output anyway.
    all_exercises = all_exercises[:10]

    return all_exercises.to_dict(orient='records')

