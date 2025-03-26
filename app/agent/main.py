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

from app.main import ChatInput
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


def send_message(chat_input: ChatInput) -> dict:
    """
    Sends a new message to the chatbot in the context of a given conversation.

    Args:
        chat_input (ChatInput): Object with the chat input data, containing:
            conversation_id (str): ID of a conversation. Subsequent calls to the same conversation will keep the message history.
            If no conversation is found for the given ID, a new one will be created.
            prompt (str): Message written by the user to be sent to the chatbot.
            integrations (Optional[list[str]]): A list of the available integrations for the interaction.
            style (Optional[str]): A key identifier for the available tutoring styles.

    Returns:
        dict: Dictionary with the output data, containing the answer of the chatbot to the user's message and other information like tool interactions, hallucinated links, etc.
    """

    # Extract input data
    conversation_id = chat_input.conversation_id
    prompt = chat_input.human_input
    integrations = chat_input.integrations if chat_input.integrations else []
    style = chat_input.style

    print("[WRAPPER]", f"Received chat request for conversation `{conversation_id}` with input `{prompt}`")
    print("[WRAPPER]", f"Enabled integrations {integrations}, and style `{style}`")

    # Reset tools results
    clear_tool_interactions(conversation_id)

    # Set up agent input
    agent_input = {'messages': [HumanMessage(content=prompt)]}
    agent_config = {'configurable': {'thread_id': conversation_id, 'integrations': integrations, 'style': style}}

    # Invoke model with given prompt and conversation_id
    agent_state = agent.invoke(input=agent_input, config=agent_config, debug=False)

    # Extract response message
    message = agent_state['messages'][-1].content

    # Log the response message
    log_message(message)

    # Fetch results obtained in the tools
    tool_interactions = get_tool_interactions(conversation_id)
    print("[WRAPPER]", f"Found {len(tool_interactions)} tool interactions")

    # Extract RAG sources from tool interactions
    rag_sources = []
    for tool_interaction in tool_interactions:
        if tool_interaction['tool_call']['name'] == 'search_integration':
            rag_sources.extend(tool_interaction['tool_response'])

    print("[WRAPPER]", "Finishing execution")

    return {
        'conversation_id': conversation_id,
        'message': message,
        'integration': agent_state['integration'],
        'style': agent_state['style'],
        'category': agent_state['category'],
        'hallucinated_links': agent_state['hallucinated_links'],
        'sources': rag_sources,
        'tool_interactions': tool_interactions,
    }


def ndjson(d: dict):
    """Converts a dict into a str by encoding it as json and adding a trailing new line."""
    return json.dumps(d) + '\n'


async def stream_send_message(chat_input: ChatInput) -> AsyncGenerator:
    """
    Sends a new message to the chatbot in the context of a given conversation and streams the events.

    Args:
        chat_input (ChatInput): Object with the chat input data, containing:
            conversation_id (str): ID of a conversation. Subsequent calls to the same conversation will keep the message history.
            If no conversation is found for the given ID, a new one will be created.
            prompt (str): Message written by the user to be sent to the chatbot.
            integrations (Optional[list[str]]): A list of the available integrations for the interaction.
            style (Optional[str]): A key identifier for the available tutoring styles.

    Returns:
        AsyncGenerator: Each item is a dict containing the key `name`, `event` and other event-specific keys.
    """

    # Extract input data
    conversation_id = chat_input.conversation_id
    prompt = chat_input.human_input
    integrations = chat_input.integrations if chat_input.integrations else []
    style = chat_input.style

    print("[WRAPPER]", f"Received stream chat request for conversation `{conversation_id}` with input `{prompt}`")
    print("[WRAPPER]", f"Enabled integrations {integrations}, and style `{style}`")

    # Reset tools results
    clear_tool_interactions(conversation_id)

    # Set up agent input
    agent_input = {'messages': [HumanMessage(content=prompt)]}
    agent_config = {'configurable': {'thread_id': conversation_id, 'integrations': integrations, 'style': style}}

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

    # Extract RAG sources from tool interactions
    rag_sources = []
    for tool_interaction in tool_interactions:
        if tool_interaction['tool_call']['name'] == 'search_integration':
            rag_sources.extend(tool_interaction['tool_response'])

    # Yield last update with the final message complete and the tool interactions
    yield ndjson({
        'name': 'report',
        'conversation_id': conversation_id,
        'message': message,
        'integration': agent_state['integration'],
        'style': agent_state['style'],
        'category': agent_state['category'],
        'hallucinated_links': agent_state['hallucinated_links'],
        'sources': rag_sources,
        'tool_interactions': tool_interactions,
    })

    print("[WRAPPER]", "Finishing execution")


if __name__ == '__main__':
    init_agent()

    ################################################################

    # Params
    method = 'sync'
    conversation_id = '1234'
    integrations = []
    style = 'iterative'

    prompt = "Help me understand matrix diagonalisation."
    followup = False
    followup_prompt = "Where do you get that information from?"

    ################################################################

    chat_input = ChatInput(conversation_id=conversation_id, human_input=prompt, integrations=integrations, style=style)

    if method == 'sync':
        message = send_message(chat_input)['message']
        print(message)

        if followup:
            chat_input.human_input = followup_prompt
            message = send_message(chat_input)['message']
            print(message)
    elif method == 'async':
        async def async_run(chat_input):
            async for update in stream_send_message(chat_input):
                print(update)

        asyncio.run(async_run(chat_input))

        if followup:
            chat_input.human_input = followup_prompt
            asyncio.run(async_run(chat_input))
