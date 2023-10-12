import json


def get_examples():
    with open('../data/examples.jsonl') as f:
        return [json.loads(line) for line in f]
