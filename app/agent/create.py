from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    AIMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain.tools import StructuredTool
from langchain_openai import ChatOpenAI

from langgraph.checkpoint import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt.tool_executor import ToolExecutor, ToolInvocation
from langgraph.prebuilt.tool_node import str_output

from app.config import config
from app.agent.prompt import system_prompt
from app.agent.cache import get_from_cache, set_to_cache
from app.agent.tool_interactions import append_tool_interaction
from app.agent.tools import search_nodes, search_news, search_exercises
from app.agent.entry import get_keywords_from_messages
from app.agent.hallucinations import get_hallucinated_links


################################################################
# State class for the agent graph                              #
################################################################

class State(TypedDict):
    """
    Class that represents a state on the graph. It holds:
        * A list of messages
        * The (full) set of results coming from a tool, whenever it applies
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]


################################################################
# Helper functions                                             #
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
                        print('[CLEANUP]', f"Found AI Message with {n_tool_calls} tool calls but not followed by {n_tool_calls} Tool Messages")
                        continue

                    # The AI Message specifies the list of tool call ids.
                    # Check that the tool messages have that same set of ids, otherwise skip to next AI Message
                    if set(tool_call_ids) != set(tool_message.tool_call_id for tool_message in tool_messages):
                        print('[CLEANUP]', f"Found AI Message with {n_tool_calls} tool calls and {n_tool_calls} subsequent Tool Messages, but their ids do not match")
                        continue

                    print('[CLEANUP]', f"Deleting tool call(s) and response(s): {[(tool_call['name'], tool_call['args']) for tool_call in messages[i].tool_calls]}")

                    # At this point, the AI Message specifies n tool call ids,
                    # and the next n messages are Tool Messages whose ids are exactly those.
                    # We delete all n + 1 messages and start over by requiring another pass
                    del messages[i: i + n_tool_calls + 1]
                    all_checked = False
                    break

    return messages


################################################################
# Main function                                                #
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
    # Tools                                                        #
    ################################################################

    tools = [
        StructuredTool.from_function(name='search_nodes', func=search_nodes),
        StructuredTool.from_function(name='search_exercises', func=search_exercises),
        StructuredTool.from_function(name='search_news', func=search_news),
    ]

    # Instantiate ToolExecutor that will be used in the 'tools' state
    tool_executor = ToolExecutor(tools)

    ################################################################
    # Memory                                                       #
    ################################################################

    memory = MemorySaver()

    ################################################################
    # Model                                                        #
    ################################################################

    # Chat model
    model = ChatOpenAI(model='gpt-4o-mini', temperature=0, openai_api_key=config['openai']['api_key'])

    # Bind tools to model
    model = model.bind_tools(tools)

    # Add system prompt to the model chain
    model = (lambda messages: [SystemMessage(content=system_prompt)] + messages) | model

    ################################################################
    # Hallucinated links                                           #
    ################################################################

    try_to_recover = True
    hallucinated_links = []

    ################################################################
    # Entry node function                                          #
    ################################################################

    def entry_node(state: State, config: RunnableConfig):
        print('[ENTRY]', "Entering entry state")

        messages = state['messages']

        # Call LLM to get a list of keywords to search nodes
        keywords_list = get_keywords_from_messages(messages)
        print('[ENTRY]', f"Forcing tool call to `search_nodes` with query=`{keywords_list}` and node_type=`None`")

        # Append manual tool call to retrieve nodes before actually calling the model
        tool_call = {
            'name': 'search_nodes',
            'args': {'query': keywords_list},
            'id': '0'
        }
        tool_call_message = AIMessage(content="", tool_calls=[tool_call])

        return {'messages': [tool_call_message]}

    ################################################################
    # Model node function                                          #
    ################################################################

    def model_node(state: State, config: RunnableConfig):
        print('[MODEL]', "Entering model state")

        # Extract the list of messages from conversation history
        messages = state['messages']

        # Try to fetch response from cache
        response = get_from_cache(messages)

        # Call LLM otherwise
        if response is None:
            print("[MODEL] Couldn't find cached response for the given message list, calling LLM")
            response = model.invoke(messages, config)
        else:
            print("[MODEL] Found cached response for the given message list, skipping LLM")

        # Set result to cache
        set_to_cache(messages, response)

        return {'messages': [response]}

    ################################################################
    # Tools node function                                          #
    ################################################################

    def tools_node(state: State, config: RunnableConfig):
        print('[TOOLS]', "Entering tools state")

        messages = state['messages']
        last_message = messages[-1]

        # Create new list of messages to be filled
        new_messages = []

        # We iterate over all tool calls in the last message, and run them storing their results
        # We know there is at least one tool call because of how the graph is built
        for tool_call in last_message.tool_calls:
            # Set up tool invocation
            action = ToolInvocation(tool=tool_call['name'], tool_input=tool_call['args'])

            # Run it
            print('[TOOLS]', f"Running tool call {tool_call['name']}")
            response = tool_executor.invoke(action)

            # Store unobfuscated result
            tool_interaction = {'tool_call': tool_call, 'tool_response': response}
            append_tool_interaction(config['configurable']['thread_id'], tool_interaction)

            # Obfuscate result - TODO Do this elsewhere by calling a function
            # for node in response['nodeset']:
            #     del node['secret']

            # Store ToolMessage in a list to be returned
            new_messages.append(ToolMessage(content=str_output(response), name=tool_call['name'], tool_call_id=tool_call['id']))

        return {'messages': new_messages}

    ################################################################
    # Recover node function                                        #
    ################################################################

    def recover_node(state: State, config: RunnableConfig):
        print('[RECOVER]', "Entering recover state")

        # Delete last message because it contains hallucinations
        state['messages'] = state['messages'][:-1]

        # Disable recovery next time to prevent running into an infinite loop
        nonlocal try_to_recover
        try_to_recover = False

        # Return new system message warning about the hallucination
        print('[RECOVER]', f"Replacing last AI message with system message warning about hallucinations, stressing invalid url {hallucinated_links[0]}")
        return {'messages': [SystemMessage(f"Make sure you only include urls present in the results from the tools. For instance, {hallucinated_links[0]} is not a valid url.")]}

    ################################################################
    # Cleanup node function                                        #
    ################################################################

    def cleanup_node(state: State, config: RunnableConfig):
        print('[CLEANUP]', "Entering cleanup state")

        # Delete AI messages with tool requests and their corresponding tool messages
        print('[CLEANUP]', "Deleting tool call requests and responses")
        state['messages'] = clean_tool_calls_and_responses(state['messages'])

        # Prepare for next execution
        nonlocal try_to_recover
        try_to_recover = True

        nonlocal hallucinated_links
        hallucinated_links = []

        return {'messages': []}

    ################################################################
    # Agent outgoing edge function                                 #
    ################################################################

    def model_edge(state: State, config: RunnableConfig):
        print('[POST-MODEL]', "Deciding what to do after model state")

        # Get last message
        messages = state['messages']
        last_message = messages[-1]

        # If there are tool calls, go to the 'tools' node
        if last_message.tool_calls:
            print('[POST-MODEL]', "There are tool calls in the last message, moving to tools state")
            return 'tools'

        # If we already tried to recover from hallucinated links, proceed to 'cleanup' node
        if not try_to_recover:
            print('[POST-MODEL]', "We already tried to recover from hallucinated links. Finishing execution to avoid infinite loops.")
            return 'cleanup'

        # If last message is not an AIMessage, proceed to 'cleanup' node
        if not isinstance(last_message, AIMessage):
            print('[POST-MODEL]', f"The last message is a {last_message.__class__}, cannot check for hallucinations. Finishing execution.")
            return 'cleanup'

        # Check for hallucinated links
        print('[POST-MODEL]', "Checking for hallucinated links")
        nonlocal hallucinated_links
        ai_messages = [message for message in messages if isinstance(message, AIMessage)]
        hallucinated_links = get_hallucinated_links(config['configurable']['thread_id'], ai_messages)

        # If no hallucinated links, proceed to 'cleanup' node
        if not hallucinated_links:
            print('[POST-MODEL]', "All links are valid. Finishing execution.")
            return 'cleanup'

        # Try to recover from hallucinated links in the 'recover' node
        print('[POST-MODEL]', f"Found some hallucinated links in the LLM message ({hallucinated_links[0]}). Moving to recover state to try to correct them.")
        return 'recover'

    ################################################################
    # State graph                                                  #
    ################################################################

    # Define a new graph
    workflow = StateGraph(State)

    # Define the two nodes we will cycle between
    workflow.add_node('entry', entry_node)
    workflow.add_node('model', model_node)
    workflow.add_node('tools', tools_node)
    workflow.add_node('recover', recover_node)
    workflow.add_node('cleanup', cleanup_node)

    # Define the edges of the graph:
    #   From START, we always go to 'entry'
    #   From 'entry', we always go to 'tools'
    #   From 'tools', we always go to 'model'
    #   From 'model', we can go to 'tools', 'recover' or 'cleanup'
    #   From 'recover', we always go to 'model'
    #   From 'cleanup', we always go to END
    workflow.set_entry_point('entry')
    workflow.add_edge(start_key='entry', end_key='tools')
    workflow.add_edge(start_key='tools', end_key='model')
    workflow.add_conditional_edges(source='model', path=model_edge)
    workflow.add_edge(start_key='recover', end_key='model')
    workflow.add_edge(start_key='cleanup', end_key=END)

    # Compile the StateGraph into a Langchain Runnable, so it can be invoked, streamed, batched and run asynchronously
    agent = workflow.compile(checkpointer=memory, debug=False)
    agent.step_timeout = 60

    return agent
