"""
This module handles the interaction with the wrapper agent of the chatbot.
More specifically, it handles the management of langchain chains (creation, retrieval, deletion) and provides an entry point to interact with them.
"""

from app.new.agent import create_agent, get_results, clear_results

# Create agent
agent = create_agent()

################################################################
# MAIN                                                         #
################################################################


def chat(conversation_id, prompt):
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
    clear_results(conversation_id)

    # Invoke model with given prompt and conversation_id
    agent_output = agent.invoke(
        input={'messages': [('human', prompt)]},
        config={'configurable': {'thread_id': conversation_id}}
    )

    # Extract response message
    message = agent_output['messages'][-1].content

    # Log the response message
    display_message = message.replace('\n', ' ')
    if len(display_message) <= 100:
        print("[WRAPPER]", f"Got response message `{display_message}` from agent executor")
    else:
        print("[WRAPPER]", f"Got response message `{display_message[:100]}...` from agent executor")

    # Fetch results obtained in the tools
    results = get_results(conversation_id)
    print("[WRAPPER]", f"Found {len(results)} results from the tools")

    return {
        'message': message,
        'results': results,
    }


if __name__ == '__main__':
    conversation_id = '1234'

    prompt = "Hey, I'm Aitor! Are there any news on the new president from EPFL?"
    print(chat(conversation_id, prompt)['message'])

    prompt = "What about exercises on differential equations?"
    print(chat(conversation_id, prompt)['message'])

    prompt = "Did I tell you my name?"
    print(chat(conversation_id, prompt)['message'])

    conversation_id = '123456'

    prompt = "Did I tell you my name?"
    print(chat(conversation_id, prompt)['message'])
