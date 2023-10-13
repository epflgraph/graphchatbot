import json


def get_prompt_examples():
    with open('../data/prompt_examples.jsonl') as f:
        return [json.loads(line) for line in f]


def get_test_examples():
    with open('../data/test_examples.jsonl') as f:
        return [json.loads(line) for line in f]
