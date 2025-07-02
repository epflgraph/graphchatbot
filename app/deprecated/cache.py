import json
from hashlib import sha256

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from app.interfaces.db import get_db_manager


def set_to_cache(messages, response):
    # Serialise list of messages and remove message ids, which should not be cached (tool call ids are cached and reused, but that's ok)
    message_dicts = [message.model_dump() for message in messages]
    message_dicts = [{k: v for k, v in message_dict.items() if k not in ['id']} for message_dict in message_dicts]
    cache_input = json.dumps(message_dicts)

    # Serialise response message (equivalent to json.dumps(message.model_dump()))
    cache_output = response.model_dump_json()

    # Hash cache input to generate cache key
    cache_key = sha256(cache_input.encode('utf-8')).hexdigest()

    # Set cache row in database
    get_db_manager().set(cache_key, {'input': cache_input, 'output': cache_output})


def get_from_cache(messages):
    # Serialise list of messages and remove message ids, which should not be cached (tool call ids are cached and reused, but that's ok)
    message_dicts = [message.model_dump() for message in messages]
    message_dicts = [{k: v for k, v in message_dict.items() if k not in ['id']} for message_dict in message_dicts]
    cache_input = json.dumps(message_dicts)

    # Hash cache input to generate cache key
    cache_key = sha256(cache_input.encode('utf-8')).hexdigest()

    # Try to fetch from database
    cache_output = get_db_manager().get(cache_key)

    # Return if not cached
    if cache_output is None:
        return None

    # Deserialise response message
    cached_response = json.loads(cache_output)

    # Return correct type of message
    message_type = cached_response['type']

    if message_type == 'human':
        response = HumanMessage(**cached_response)
    elif message_type == 'ai':
        response = AIMessage(**cached_response)
    elif message_type == 'system':
        response = SystemMessage(**cached_response)
    elif message_type == 'tool':
        response = ToolMessage(**cached_response)
    else:
        response = None

    return response
