import random

from app.data import get_prompt_examples, get_test_examples
from app.conversation import (
    get_chain,
    parse_instructions,
    follow_instructions,
    build_context,
)


def test_instructions():
    # Check generation of instructions on a randomly sampled set of test examples
    examples = get_test_examples()
    examples = random.sample(examples, 3)

    for example in examples:
        # Use list index as conversation id
        conversation_id = str(examples.index(example))
        chain = get_chain('instructions', conversation_id)

        # Run chain with human message
        instructions_str = chain({'input': example['query']})['text']
        instructions = instructions_str.split('\n')

        # Check if returned instructions match the expected ones
        assert instructions == example['instructions']


def test_examples():
    examples = get_prompt_examples() + get_test_examples()

    for example in examples:
        # Parse instructions
        instructions_str = '\n'.join(example['instructions'])
        instructions = parse_instructions(instructions_str)

        ################

        # Follow instructions
        nodesets = follow_instructions(instructions)

        # Check nodesets is a list
        assert isinstance(nodesets, list)

        # Check there is at least one nodeset
        assert len(nodesets) > 0

        # Check the first nodeset is a list
        assert isinstance(nodesets[0], list)

        # Check the first nodeset is not empty
        assert len(nodesets[0]) > 0

        ################

        # Build context
        contexts = build_context(instructions)

        # Check contexts are the same as expected
        print(contexts)
        assert contexts == example['contexts']
