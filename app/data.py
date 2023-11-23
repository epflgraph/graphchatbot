import json


def get_examples(which):
    with open(f'../data/{which}_examples.jsonl') as f:
        return [json.loads(line) for line in f]
