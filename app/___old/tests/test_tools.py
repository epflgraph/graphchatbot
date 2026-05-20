from app.agent.tools import (
    search_nodes,
    search_exercises,
    search_news,
    search_plan,
)

from conftest import tool_inputs


# Nodes tool
def test_nodes():
    for tool_input in tool_inputs['search_nodes']:
        tool_output = search_nodes(keywords=tool_input['keywords'], node_type=tool_input['node_type'])

        assert isinstance(tool_output, list)
        assert len(tool_output) > 0
        assert isinstance(tool_output[0], dict)
        assert all([field in tool_output[0] for field in ['type', 'id', 'name_en', 'name_fr', 'short_description', 'url', 'nearest_nodes']])


# Exoset tool
def test_exoset():
    for tool_input in tool_inputs['search_exercises']:
        tool_output = search_exercises(query=tool_input['query'])

        assert isinstance(tool_output, list)
        assert len(tool_output) > 0
        assert isinstance(tool_output[0], dict)
        assert all([field in tool_output[0] for field in ['title', 'url', 'score']])


# News tool
def test_news():
    for tool_input in tool_inputs['search_news']:
        tool_output = search_news(query=tool_input['query'])

        assert isinstance(tool_output, list)
        assert len(tool_output) > 0
        assert isinstance(tool_output[0], dict)
        assert all([field in tool_output[0] for field in ['title', 'url', 'snippet']])


# Plan tool
def test_plan():
    for tool_input in tool_inputs['search_plan']:
        tool_output = search_plan(query=tool_input['query'])

        assert isinstance(tool_output, dict)
        assert 'url' in tool_output
        assert isinstance(tool_output['url'], str)
        assert 'https://plan.epfl.ch/' in tool_output['url']
