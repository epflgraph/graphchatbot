from app.tools import ask_graph
from app.tools.graph import graph_answers
from app.data import get_examples


def test_ask_graph():
    examples = get_examples('prompt') + get_examples('test')

    for example in examples:
        # Check obfuscated result returned by the function
        obfuscated_result = ask_graph(example['query'])

        assert 'nodeset' in obfuscated_result
        assert isinstance(obfuscated_result['nodeset'], list)
        assert len(obfuscated_result['nodeset']) > 0

        assert 'context' in obfuscated_result
        assert isinstance(obfuscated_result['context'], dict)
        assert len(obfuscated_result['context']) > 0

        # Check full result stored on the side
        assert example['query'] in graph_answers

        full_result = graph_answers[example['query']]

        assert 'nodeset' in full_result
        assert isinstance(full_result['nodeset'], list)
        assert len(full_result['nodeset']) > 0

        assert 'nodesets' in full_result
        assert isinstance(full_result['nodesets'], dict)
        assert len(full_result['nodesets']) > 0

        assert 'instructions_str' in full_result
        assert isinstance(full_result['instructions_str'], str)
        assert len(full_result['instructions_str']) > 0
        print(full_result['instructions_str'].split('\n'))
        print(example['instructions'])
        assert full_result['instructions_str'].split('\n') == example['instructions']

        assert 'context' in full_result
        assert isinstance(full_result['context'], dict)
        assert len(full_result['context']) > 0
        print(full_result['context'])
        print(example['context'])
        assert full_result['context'] == example['context']
