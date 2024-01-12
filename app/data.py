"""
This module contains utils to read data from the examples in the `data` folder.
"""

import json


def get_examples(which):
    with open(f'../data/{which}_examples.jsonl') as f:
        return [json.loads(line) for line in f]
