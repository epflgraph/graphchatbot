"""
This module creates and manages the agent that serves all chat requests.
It is created as a LangGraph StateGraph with custom functions on their nodes and edges.
It also provides the entry point function to interact with it.
"""
import json
from hashlib import sha256
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain.tools import StructuredTool
from langchain_openai import ChatOpenAI

from langgraph.checkpoint import MemorySaver
from langgraph.checkpoint.base import empty_checkpoint
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt.tool_executor import ToolExecutor, ToolInvocation
from langgraph.prebuilt.tool_node import str_output

from app.config import config
from app.interfaces.db import db_manager
from app.prompt import system_prompt
from app.tools import search_nodes, search_news, search_exercises

agent = None
agent_results = {}

################################################################


def append_results(thread_id, results):
    agent_results.setdefault(thread_id, [])
    agent_results[thread_id].append(results)


def get_results(thread_id):
    return agent_results.get(thread_id, [])


def clear_results(thread_id):
    agent_results[thread_id] = []


################################################################

def set_to_cache(messages, response):
    # Serialise list of messages and remove message ids, which should not be cached (tool call ids are cached and reused, but that's ok)
    message_dicts = [message.dict() for message in messages]
    message_dicts = [{k: v for k, v in message_dict.items() if k not in ['id']} for message_dict in message_dicts]
    cache_input = json.dumps(message_dicts)

    # Serialise response message (equivalent to json.dumps(message.dict()))
    cache_output = response.json()

    # Hash cache input to generate cache key
    cache_key = sha256(cache_input.encode('utf-8')).hexdigest()

    # Set cache row in database
    db_manager.set(cache_key, {'input': cache_input, 'output': cache_output})


def get_from_cache(messages):
    # Serialise list of messages and remove message ids, which should not be cached (tool call ids are cached and reused, but that's ok)
    message_dicts = [message.dict() for message in messages]
    message_dicts = [{k: v for k, v in message_dict.items() if k not in ['id']} for message_dict in message_dicts]
    cache_input = json.dumps(message_dicts)

    # Hash cache input to generate cache key
    cache_key = sha256(cache_input.encode('utf-8')).hexdigest()

    # Try to fetch from database
    cache_output = db_manager.get(cache_key)

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

################################################################


def create_agent():
    """
    This function creates a custom agent with the custom tools from EPFL Graph's use case.
    The agent is a LangChain Runnable, and it is created using LangGraph.
    Conceptually, it is very similar to LangGraph's prebuilt ReAct agent, but instead of a ToolNode it uses a ToolExecutor
    to have more control over the function that is run on the 'tools' node, similarly to LangGraph's Human-in-the-loop example.

    Related links:
      * LangGraph's prebuilt ReAct agent: https://langchain-ai.github.io/langgraph/reference/prebuilt/#create_react_agent
      * LangGraph's prebuilt ToolNode: https://langchain-ai.github.io/langgraph/reference/prebuilt/#toolnode
      * LangGraph's prebuilt ToolExecutor: https://langchain-ai.github.io/langgraph/reference/prebuilt/#toolexecutor
      * LangGraph's Human-in-the-loop example post: https://blog.langchain.dev/human-in-the-loop-with-opengpts-and-langgraph/
      * LangGraph's Human-in.the-loop example notebook: https://github.com/langchain-ai/langgraph/blob/main/examples/human-in-the-loop.ipynb
    """

    ################################################################
    # Chat model                                                   #
    ################################################################

    model = ChatOpenAI(temperature=0, openai_api_key=config['openai']['api_key'])

    ################################################################
    # Tools                                                        #
    ################################################################

    tools = [
        StructuredTool.from_function(name='search_nodes', func=search_nodes),
        StructuredTool.from_function(name='search_exercises', func=search_exercises),
        StructuredTool.from_function(name='search_news', func=search_news),
    ]

    ################################################################
    # Memory                                                       #
    ################################################################

    memory = MemorySaver()

    ################################################################
    # State graph                                                  #
    ################################################################

    class State(TypedDict):
        """
        Class that represents a state on the graph. It holds:
            * A list of messages
            * The (full) set of results coming from a tool, whenever it applies
        """

        messages: Annotated[Sequence[BaseMessage], add_messages]

    ################################################################

    # Bind tools to model
    model = model.bind_tools(tools)

    # Add system prompt to the model chain
    model = (lambda messages: [SystemMessage(content=system_prompt)] + messages) | model

    # Instantiate ToolExecutor that will be used in the 'tools' state
    tool_executor = ToolExecutor(tools)

    ################################################################

    def clean_tool_calls_and_responses(messages):
        # Start setting flag to mark when we will be done checking
        all_checked = False
        while not all_checked:
            # Assume this is the last pass
            all_checked = True

            # Iterate over all messages, search first AI Message with tool calls
            for i in range(len(messages) - 1):
                if isinstance(messages[i], AIMessage) and messages[i].tool_calls:
                    tool_call_ids = [tool_call['id'] for tool_call in messages[i].tool_calls]
                    n_tool_calls = len(tool_call_ids)

                    # Make sure there are enough messages after the AI Message
                    if i + n_tool_calls <= len(messages) - 1:
                        tool_messages = messages[i + 1: i + n_tool_calls + 1]

                        # Check all tool messages are indeed Tool Messages, otherwise skip to next AI Message
                        if not all(map(lambda x: isinstance(x, ToolMessage), tool_messages)):
                            print(f"[AGENT] Found AI Message with {n_tool_calls} tool calls but not followed by {n_tool_calls} Tool Messages")
                            continue

                        # The AI Message specifies the list of tool call ids.
                        # Check that the tool messages have that same set of ids, otherwise skip to next AI Message
                        if set(tool_call_ids) != set(tool_message.tool_call_id for tool_message in tool_messages):
                            print(f"[AGENT] Found AI Message with {n_tool_calls} tool calls and {n_tool_calls} subsequent Tool Messages, but their ids do not match")
                            continue

                        print(f"[AGENT] Deleting tool call(s) and response(s): {[(tool_call['name'], tool_call['args']) for tool_call in messages[i].tool_calls]}")

                        # At this point, the AI Message specifies n tool call ids,
                        # and the next n messages are Tool Messages whose ids are exactly those.
                        # We delete all n + 1 messages and start over by requiring another pass
                        del messages[i: i + n_tool_calls + 1]
                        all_checked = False
                        break

        return messages

    # Define the function that will run in the 'agent' node
    def call_model(state: State, config: RunnableConfig):
        print(f"[AGENT] Entering agent state")

        # Extract the list of messages from conversation history
        messages = state['messages']

        # Try to fetch response from cache
        response = get_from_cache(messages)

        # Call LLM otherwise
        if response is None:
            print("[AGENT] Couldn't find cached response for the given message list, calling LLM")
            response = model.invoke(messages, config)
        else:
            print("[AGENT] Found cached response for the given message list, skipping LLM")

        # Set result to cache
        set_to_cache(messages, response)

        # Clean up the tool requests and responses if there are no more tool calls
        if not response.tool_calls:
            state['messages'] = clean_tool_calls_and_responses(messages)

        return {'messages': [response]}

    ################################################################

    # Define the function that will run in the 'agent' node
    def call_tools(state: State, config: RunnableConfig):
        print(f"[TOOLS] Entering tools state")

        messages = state['messages']
        last_message = messages[-1]

        # Create new state to be filled with messages
        new_state = {
            'messages': []
        }

        # We iterate over all tool calls in the last message, and run them storing their results
        # We know there is at least one tool call because of how the graph is built
        for tool_call in last_message.tool_calls:
            # Set up tool invocation
            action = ToolInvocation(tool=tool_call['name'], tool_input=tool_call['args'])

            # Run it
            print(f"[TOOLS] Running tool call {tool_call['name']}")
            response = tool_executor.invoke(action)

            # Store unobfuscated result
            append_results(config['configurable']['thread_id'], response)

            # Obfuscate result - TODO Do this elsewhere by calling a function
            # for node in response['nodeset']:
            #     del node['secret']

            # Store ToolMessage in a list to be returned
            new_state['messages'].append(ToolMessage(content=str_output(response), name=tool_call['name'], tool_call_id=tool_call['id']))

        return new_state

    ################################################################

    # Define the function to decide where to go from the 'agent' node
    def agent_target_node(state: State):
        print("[POST-AGENT] Deciding what to do after agent state")

        messages = state['messages']
        last_message = messages[-1]

        # If there are tool calls, go to the 'tools' node
        if last_message.tool_calls:
            print("[POST-AGENT] There are tool calls in the last message, moving to tools state")
            return 'tools'

        # Otherwise finish execution
        print("[POST-AGENT] There are tool calls in the last message, moving to END state")
        return END

    ################################################################

    # Define a new graph
    workflow = StateGraph(State)

    # Define the two nodes we will cycle between
    workflow.add_node('agent', call_model)
    workflow.add_node('tools', call_tools)

    # Set the entrypoint as 'agent'. This means that this node is the first one called.
    workflow.set_entry_point('agent')

    # Define the edges of the graph
    #   From 'agent', we can go to 'tools' or END
    #   From 'tools', we always go to 'agent'
    workflow.add_conditional_edges(source='agent', path=agent_target_node)
    workflow.add_edge(start_key='tools', end_key='agent')

    # Compile the StateGraph into a Langchain Runnable, so it can be invoked, streamed, batched and run asynchronously
    global agent
    agent = workflow.compile(checkpointer=memory, debug=False)
    agent.step_timeout = 60


################################################################

def generate_context(message, results):
    message_nodes = []

    # Keep only nodes and links that appear in the message
    for nodes in results:
        for node in nodes:
            message_node_links = []
            for link in node['links']:
                if link['url'] in message:
                    message_node_links.append(link)

            if message_node_links or node['url'] in message:
                message_nodes.append({**node, 'links': message_node_links, 'match': node['url'] in message})

    # Gather the node types of links for all links of each node
    for node in message_nodes:
        link_types = []
        for link in node['links']:
            if link['type'] not in link_types:
                link_types.append(link['type'])
        node['link_types'] = link_types
        node['link_count'] = len(node['links'])

    return message_nodes


def generate_node_context_message(message_node):
    # Case where node links are mentioned
    if len(message_node['link_types']) > 0:
        # Generate subsrting for related node types
        link_types = [f"{link_type}s" for link_type in message_node['link_types']]
        if len(message_node['link_types']) == 1:
            link_types = link_types[0]
        else:
            link_types = f"{', '.join(link_types[:-1])} and {link_types[-1]}"

        # Return string including or not the node
        if message_node['match']:
            return f"""Showing the {message_node['type']} "{message_node['name_en']}" with related {link_types}"""
        else:
            return f"""Showing {link_types} related to the {message_node['type']} "{message_node['name_en']}\""""

    # Case where node links are not mentioned
    if message_node['match']:
        return f"""Showing the {message_node['type']} "{message_node['name_en']}\""""

    # Should never get here
    return ''


def generate_context_messages(message_nodes):
    return [generate_node_context_message(message_node) for message_node in message_nodes]

################################################################


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
    clear_results(conversation_id)

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
    results = get_results(conversation_id)
    print("[WRAPPER]", f"Found {len(results)} results from the tools")

    # Generate context to be displayed in the frontend
    context = generate_context(message, results)
    context_message = generate_context_messages(context)

    return {
        'message': message,
        'results': results,
        'context': context,
        'context_message': context_message,
    }


def clear_conversation(conversation_id: str) -> bool:
    checkpoint = empty_checkpoint()
    agent.checkpointer.put(config={'configurable': {'thread_id': conversation_id}}, checkpoint=checkpoint, metadata={})

    return True


if __name__ == '__main__':
    create_agent()

    print(send_message('1234', "Show me lectures about the Fourier transform")['message'])

    print(send_message('1234', "Now exercises")['message'])
