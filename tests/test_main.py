from app.data import get_examples
from app.conversation import (
    parse_instructions,
    follow_instructions,
    build_context,
)


def test_examples():
    examples = get_examples()

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
        assert contexts == example['contexts']
