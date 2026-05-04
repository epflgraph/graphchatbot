import asyncio
import json
import time
from typing import AsyncGenerator

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from openai.types.chat.completion_create_params import CompletionCreateParams

from app.bots.base import Bot
from app.config import config

langfuse = Langfuse(
    host=config.get('langfuse', {}).get('host'),
    secret_key=config.get('langfuse', {}).get('secret_key'),
    public_key=config.get('langfuse', {}).get('public_key'),
    environment=config.get('langfuse', {}).get('environment'),
)

MODEL_NODES = ('model',)


async def generate_completion(chat_request: CompletionCreateParams, bot: Bot) -> dict:
    print('[BOTS]', f"Received non-streaming request for bot `{bot.name}` with last message `{chat_request['messages'][-1]['content']}`")

    agent_input = {'messages': chat_request['messages']}
    agent_config = {
        'callbacks': [CallbackHandler()],
        'metadata': {'langfuse_tags': [bot.name]},
    }

    agent_state = await bot.graph.ainvoke(input=agent_input, config=agent_config, context=bot)
    content = agent_state['messages'][-1].content

    return {
        'id': '1',
        'object': 'chat.completion',
        'created': time.time(),
        'model': chat_request['model'],
        'choices': [{'message': {'role': 'assistant', 'content': content}}],
    }


async def agenerate_completion(chat_request: CompletionCreateParams, bot: Bot) -> AsyncGenerator:
    print('[BOTS]', f"Received streaming request for bot `{bot.name}` with last message `{chat_request['messages'][-1]['content']}`")

    agent_input = {'messages': chat_request['messages']}
    agent_config = {
        'callbacks': [CallbackHandler()],
        'metadata': {'langfuse_tags': [bot.name]},
    }

    content = ''

    try:
        async for event in bot.graph.astream_events(input=agent_input, config=agent_config, context=bot, version='v2'):
            langgraph_node = event['metadata'].get('langgraph_node')
            event_name = event.get('name')
            event_type = event.get('event')

            if langgraph_node in MODEL_NODES and event_name == 'ChatOpenAI' and event_type == 'on_chat_model_stream':
                try:
                    chunk_text = event['data']['chunk'].text
                except Exception:
                    chunk_text = ''

                chunk = {
                    'id': '1',
                    'object': 'chat.completion.chunk',
                    'created': time.time(),
                    'model': chat_request['model'],
                    'choices': [{'delta': {'content': chunk_text}}],
                }

                content += chunk_text
                yield f"data: {json.dumps(chunk)}\n\n"

    except asyncio.CancelledError:
        print('[BOTS]', "Client disconnected, stream cancelled")
    except Exception as e:
        print('[BOTS]', e)
    finally:
        print(content)
        yield "data: [DONE]\n\n"
