"""
This module creates and manages the agent that serves all chat requests.
It is created as a LangGraph StateGraph with custom functions on their nodes and edges.
It also provides the entry point function to interact with it.
"""

import asyncio
import json
from typing import AsyncGenerator

from langchain_core.messages import (
    HumanMessage,
)

from langgraph.checkpoint.base import empty_checkpoint

from app.agent.tool_interactions import get_tool_interactions, clear_tool_interactions
from app.agent.create import create_agent

agent = None


def init_agent():
    global agent
    agent = create_agent()


def send_message(conversation_id: str, prompt: str) -> dict:
    """
    Sends a new message to the chatbot in the context of a given conversation.

    Args:
        conversation_id (str): ID of a conversation. Subsequent calls to the same conversation will keep the message history.
        If no conversation is found for the given ID, a new one will be created.
        prompt (str): Message written by the user to be sent to the chatbot.

    Returns:
        dict: Dictionary with keys `message` and `results`, containing the answer of the chatbot to the user's message and information about the
        returned nodes if applicable, respectively.
    """

    print("[WRAPPER]", f"Received chat request for conversation `{conversation_id}` with input `{prompt}`")

    # Reset tools results
    clear_tool_interactions(conversation_id)

    # Invoke model with given prompt and conversation_id
    agent_output = agent.invoke(
        input={'messages': [HumanMessage(content=prompt)]},
        config={'configurable': {'thread_id': conversation_id}},
        debug=False
    )

    # Extract response message
    message = agent_output['messages'][-1].content

    # Log the response message
    display_message = message.replace('\n', ' ')
    if len(display_message) <= 100:
        print("[WRAPPER]", f"Got response message `{display_message}` from agent system")
    else:
        print("[WRAPPER]", f"Got response message `{display_message[:100]}...` from agent system")

    # Fetch results obtained in the tools
    tool_interactions = get_tool_interactions(conversation_id)
    print("[WRAPPER]", f"Found {len(tool_interactions)} tool interactions")

    return {
        'message': message,
        'tool_interactions': tool_interactions,
    }


def ndjson(d: dict):
    """Converts a dict into a str by encoding it as json and adding a trailing new line."""
    return json.dumps(d) + '\n'


async def stream_send_message(conversation_id: str, prompt: str) -> AsyncGenerator:
    """
    Sends a new message to the chatbot in the context of a given conversation and streams the events.

    Args:
        conversation_id (str): ID of a conversation. Subsequent calls to the same conversation will keep the message history.
        If no conversation is found for the given ID, a new one will be created.
        prompt (str): Message written by the user to be sent to the chatbot.

    Returns:
        AsyncGenerator: Each item is a dict containing the key 'state' and possibly 'content'.
    """

    print("[WRAPPER]", f"Received stream chat request for conversation `{conversation_id}` with input `{prompt}`")

    # Reset tools results
    clear_tool_interactions(conversation_id)

    # Set up agent input
    agent_input = {'messages': [HumanMessage(content=prompt)]}
    agent_config = {'configurable': {'thread_id': conversation_id}}

    # Define states to be checked
    states = ['entry', 'tools', 'model', 'model_edge', 'recover', 'cleanup']
    state = None
    last_event = None
    async for event in agent.astream_events(input=agent_input, config=agent_config, version='v2'):
        last_event = event

        # Yield when there is a change in the graph state
        if event['name'] in states and event['event'] == 'on_chain_start':
            state = event['name']
            yield ndjson({'state': state})

        # Yield in the model state when there is a message chunk
        if state == 'model' and event['name'] == 'ChatOpenAI' and event['event'] == 'on_chat_model_stream':
            yield ndjson({'state': state, 'content': event['data']['chunk'].content})

    # Extract response message
    content = last_event['data']['output']['messages'][-1].content

    # Log the response message
    display_content = content.replace('\n', ' ')
    if len(content) <= 100:
        print("[WRAPPER]", f"Got response message `{display_content}` from agent system")
    else:
        print("[WRAPPER]", f"Got response message `{display_content[:100]}...` from agent system")

    # Fetch results obtained in the tools
    tool_interactions = get_tool_interactions(conversation_id)
    print("[WRAPPER]", f"Found {len(tool_interactions)} tool interactions")

    # Yield last update with the final message complete and the tool interactions
    yield ndjson({
        'state': 'end',
        'content': content,
        'tool_interactions': tool_interactions,
    })


if __name__ == '__main__':
    init_agent()

    prompt = "Why is 1.99999... equal to 2?"

    # Sync
    # print(send_message('1234', prompt)['message'])
    # print(send_message('1234', "Why is it log_3(2)?")['message'])

    # Async
    async def f():
        async for update in stream_send_message('1234', prompt):
            print(update)

    asyncio.run(f())
