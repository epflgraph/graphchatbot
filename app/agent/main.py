"""
This module creates and manages the agent that serves all chat requests.
It is created as a LangGraph StateGraph with custom functions on their nodes and edges.
It also provides the entry point function to interact with it.
"""

import asyncio
import json
import time
from typing import AsyncGenerator

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.integrations import IntegrationConfig

from app.agent.create import create_agent

from app.config import config

agent = None

# Initialise langfuse client and callback handler
langfuse = Langfuse(
    host=config.get('langfuse', {}).get('host'),
    secret_key=config.get('langfuse', {}).get('secret_key'),
    public_key=config.get('langfuse', {}).get('public_key'),
    environment=config.get('langfuse', {}).get('environment'),
)


def init_agent():
    global agent
    agent = create_agent()


async def generate_completion(chat_request) -> dict:
    print('[WRAPPER]', f"Received non-streaming request for model `{chat_request['model']}` with last message `{chat_request['messages'][-1]['content']}`")
    # print(chat_request)

    # Set up agent input
    agent_input = {'messages':  chat_request['messages']}
    agent_config = {
        'configurable': {
            'integration': IntegrationConfig.from_name(chat_request['model']),
        },
        'callbacks': [CallbackHandler()],
        'metadata': {'langfuse_tags': [chat_request['model']]},
    }

    # Invoke model with given prompt and conversation_id
    agent_state = await agent.ainvoke(input=agent_input, config=agent_config)

    # Extract last message
    content = agent_state['messages'][-1].content

    return {
        "id": "1",
        "object": "chat.completion",
        "created": time.time(),
        "model": chat_request['model'],
        "choices": [{"message": {'role': 'assistant', 'content': content}}],
    }


async def agenerate_completion(chat_request) -> AsyncGenerator:
    print('[WRAPPER]', f"Received streaming request for model `{chat_request['model']}` with last message `{chat_request['messages'][-1]['content']}`")
    # print(chat_request)

    # Set up agent input
    agent_input = {'messages':  chat_request['messages']}
    agent_config = {
        'configurable': {'integration': IntegrationConfig.from_name(chat_request['model'])},
        'callbacks': [CallbackHandler()],
        'metadata': {'langfuse_tags': [chat_request['model']]},
    }

    # Launch agent and iterate over the event updates
    content = ''

    try:
        async for event in agent.astream_events(input=agent_input, config=agent_config, version='v2'):
            langgraph_node = event['metadata'].get('langgraph_node')
            event_name = event.get('name')
            event_type = event.get('event')

            # Yield for new messages in premodel or postmodel states
            if langgraph_node in ('premodel', 'postmodel') and event_name in ('premodel', 'postmodel') and event_type == 'on_chain_end':
                try:
                    chunk_content = event['data']['output'].update['messages'][-1].content
                except Exception:
                    chunk_content = ''

                chunk = {
                    'id': "1",
                    'object': "chat.completion.chunk",
                    'created': time.time(),
                    'model': chat_request['model'],
                    'choices': [{'delta': {'content': chunk_content}}],
                }

                content += chunk_content
                yield f"data: {json.dumps(chunk)}\n\n"

            # Yield in the model node when there is a message chunk
            if langgraph_node == 'model' and event_name == 'ChatOpenAI' and event_type == 'on_chat_model_stream':
                try:
                    chunk_text = event['data']['chunk'].text()
                except Exception:
                    chunk_text = ''

                chunk = {
                    'id': "1",
                    'object': "chat.completion.chunk",
                    'created': time.time(),
                    'model': chat_request['model'],
                    'choices': [{'delta': {'content': chunk_text}}],
                }

                content += chunk_text
                yield f"data: {json.dumps(chunk)}\n\n"

    except asyncio.CancelledError:
        # Client disconnected, nothing else to do
        print('[WRAPPER]', "Client disconnected, stream cancelled")
    except Exception as e:
        print('[WRAPPER]', e)
    finally:
        print(content)
        yield "data: [DONE]\n\n"


if __name__ == '__main__':
    init_agent()

    ################################################################

    # Params
    method = 'sync'
    chat_request = {
        'model': 'lex',
        'messages': [{'role': 'user', 'content': 'Heeeeello'}]
    }

    ################################################################

    if method == 'sync':
        print(generate_completion(chat_request))
    else:
        async def async_run(chat_request):
            async for update in agenerate_completion(chat_request):
                print(update)

        asyncio.run(async_run(chat_request))
