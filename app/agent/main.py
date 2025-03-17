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

from app.agent.tool_interactions import get_tool_interactions, clear_tool_interactions
from app.agent.create import create_agent

agent = None


def init_agent():
    global agent
    agent = create_agent()


def log_message(message):
    display_message = message.replace('\n', ' ')
    if len(display_message) <= 100:
        print("[WRAPPER]", f"Got response message `{display_message}` from agent system")
    else:
        print("[WRAPPER]", f"Got response message `{display_message[:100]}...` from agent system")


def send_message(conversation_id: str, prompt: str, integrations: list[str] = None) -> dict:
    """
    Sends a new message to the chatbot in the context of a given conversation.

    Args:
        conversation_id (str): ID of a conversation. Subsequent calls to the same conversation will keep the message history.
        If no conversation is found for the given ID, a new one will be created.
        prompt (str): Message written by the user to be sent to the chatbot.
        integrations (list[str]): A list of the available integrations for the interaction.

    Returns:
        dict: Dictionary with keys `message` and `results`, containing the answer of the chatbot to the user's message and information about the
        returned nodes if applicable, respectively.
    """

    print("[WRAPPER]", f"Received chat request for conversation `{conversation_id}` with input `{prompt}`")

    # Reset tools results
    clear_tool_interactions(conversation_id)

    # Invoke model with given prompt and conversation_id
    agent_state = agent.invoke(
        input={'messages': [HumanMessage(content=prompt)]},
        config={'configurable': {'thread_id': conversation_id, 'integrations': integrations}},
        debug=False
    )

    # Extract response message
    message = agent_state['messages'][-1].content

    # Log the response message
    log_message(message)

    # Fetch results obtained in the tools
    tool_interactions = get_tool_interactions(conversation_id)
    print("[WRAPPER]", f"Found {len(tool_interactions)} tool interactions")

    print("[WRAPPER]", "Finishing execution")

    return {
        'conversation_id': conversation_id,
        'message': message,
        'tool_interactions': tool_interactions,
        'integration': agent_state['integration'],
        'category': agent_state['category'],
        'hallucinated_links': agent_state['hallucinated_links'],
    }


def ndjson(d: dict):
    """Converts a dict into a str by encoding it as json and adding a trailing new line."""
    return json.dumps(d) + '\n'


async def stream_send_message(conversation_id: str, prompt: str, integrations: list[str] = None) -> AsyncGenerator:
    """
    Sends a new message to the chatbot in the context of a given conversation and streams the events.

    Args:
        conversation_id (str): ID of a conversation. Subsequent calls to the same conversation will keep the message history.
        If no conversation is found for the given ID, a new one will be created.
        prompt (str): Message written by the user to be sent to the chatbot.
        integrations (list[str]): A list of the available integrations for the interaction.

    Returns:
        AsyncGenerator: Each item is a dict containing the key 'state' and possibly 'content'.
    """

    print("[WRAPPER]", f"Received stream chat request for conversation `{conversation_id}` with input `{prompt}`")

    # Reset tools results
    clear_tool_interactions(conversation_id)

    # Set up agent input
    agent_input = {'messages': [HumanMessage(content=prompt)]}
    agent_config = {'configurable': {'thread_id': conversation_id, 'integrations': integrations}}

    # Define states to be checked
    node_names = ['supervisor', 'classify', 'model', 'tools', 'check', 'cleanup']
    current_node = None
    last_event = None
    async for event in agent.astream_events(input=agent_input, config=agent_config, version='v2'):
        # Yield when we enter a node
        if event['name'] in node_names and event['event'] == 'on_chain_start':
            current_node = event['name']

            if event['name'] == 'tools':
                tool_calls = [{'name': tool_call['name'], 'args': tool_call['args']} for tool_call in event['data']['input']['messages'][-1].tool_calls]
                yield ndjson({'name': current_node, 'event': 'start', 'tool_calls': tool_calls})
            else:
                yield ndjson({'name': current_node, 'event': 'start'})

        # Yield in the model node when there is a message chunk
        if current_node == 'model' and event['name'] == 'ChatOpenAI' and event['event'] == 'on_chat_model_stream':
            yield ndjson({'name': current_node, 'event': 'stream', 'content': event['data']['chunk'].content})

        # Yield when we exit a node
        if event['name'] in node_names and event['event'] == 'on_chain_end':
            if event['name'] == 'classify':
                yield ndjson({'name': event['name'], 'event': 'end', 'request_type': event['data']['output'].update['category']})
            elif event['name'] == 'check':
                hallucinated_links = event['data']['output'].update['hallucinated_links']   # TODO return this list instead of `need_to_regenerate`
                yield ndjson({'name': event['name'], 'event': 'end', 'need_to_regenerate': False})
            else:
                yield ndjson({'name': event['name'], 'event': 'end'})

        # Store event in case it is the last one, so we can yield it later
        last_event = event

    # Extract response message
    agent_state = last_event['data']['output']
    message = agent_state['messages'][-1].content

    # Log the response message
    log_message(message)

    # Fetch results obtained in the tools
    tool_interactions = get_tool_interactions(conversation_id)
    print("[WRAPPER]", f"Found {len(tool_interactions)} tool interactions")

    # Yield last update with the final message complete and the tool interactions
    yield ndjson({
        'name': 'report',
        'conversation_id': conversation_id,
        'message': message,
        'tool_interactions': tool_interactions,
        'integration': agent_state['integration'],
        'category': agent_state['category'],
        'hallucinated_links': agent_state['hallucinated_links'],
    })

    print("[WRAPPER]", "Finishing execution")


if __name__ == '__main__':
    init_agent()

    conversation_id = '1234'
    integrations = ['lex']

    method = 'async'

    prompt = "How many days off am I entitled to if I have a baby?"

    followup = False
    followup_prompt = "Where do you get that information from?"

    if method == 'sync':
        message = send_message(conversation_id, prompt, integrations)['message']
        print(message)

        if followup:
            message = send_message(conversation_id, followup_prompt, integrations)['message']
            print(message)
    elif method == 'async':
        async def async_run(prompt):
            async for update in stream_send_message(conversation_id, prompt, integrations):
                print(update)

        asyncio.run(async_run(prompt))

        if followup:
            asyncio.run(async_run(followup_prompt))
