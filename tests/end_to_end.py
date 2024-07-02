from fastapi.testclient import TestClient

from app.main import app

from conftest import end_to_end_prompts


def test_end_to_end():
    with TestClient(app) as client:
        for prompt in end_to_end_prompts:
            # Reset conversation
            payload = {'conversation_id': 'test'}
            response = client.post('/reset', json=payload)
            assert response.status_code == 200

            # Chat using prompt
            payload = {'human_input': prompt, 'conversation_id': 'test'}
            response = client.post('/chat', json=payload)
            assert response.status_code == 200

            response = response.json()
            assert isinstance(response, dict)

            assert 'message' in response
            assert isinstance(response['message'], str)
            assert len(response['message']) > 0

            assert 'tool_interactions' in response
            assert isinstance(response['tool_interactions'], list)
            assert len(response['tool_interactions']) > 0
