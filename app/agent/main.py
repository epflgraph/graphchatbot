"""
This module creates and manages the agent that serves all chat requests.
It is created as a LangGraph StateGraph with custom functions on their nodes and edges.
It also provides the entry point function to interact with it.
"""

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


def clear_conversation(conversation_id: str) -> bool:
    checkpoint = empty_checkpoint()
    agent.checkpointer.put(config={'configurable': {'thread_id': conversation_id}}, checkpoint=checkpoint, metadata={})

    return True


if __name__ == '__main__':
    init_agent()

    print(send_message('1234', "What is the Hausdorff dimension? How do I compute the Hausdorff dimension of the Cantor set?")['message'])

    # print(send_message('1234', "Why is it log_3(2)?")['message'])
