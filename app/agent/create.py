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
from app.tools import search_nodes, search_news, search_exercises


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
            tool_interaction = {'tool_call': tool_call, 'tool_response': response}
            append_tool_interaction(config['configurable']['thread_id'], tool_interaction)

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
    agent = workflow.compile(checkpointer=memory, debug=False)
    agent.step_timeout = 60

    return agent
