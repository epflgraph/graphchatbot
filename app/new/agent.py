"""
This module creates and manages the agent that serves all chat requests.
It is created as a LangGraph StateGraph with custom functions on their nodes and edges.
It also provides the entry point function to interact with it.
"""

from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
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
from app.new.prompt import system_prompt
from app.tools import search_news, search_exercises


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
        # StructuredTool.from_function(name='Ask_EPFL_Graph', func=ask_graph, description="Useful to ask the knowledge graph of EPFL in natural language"),
        StructuredTool.from_function(name='Search_EXOSET_Exercises', func=search_exercises, description="Useful to find references to exercises in EXOSET, the exercises database of EPFL, that are related to a given concept. Always provide the language spoken by the user"),
        # StructuredTool.from_function(name='Find_Person_Favourite_Color', func=find_color, description="Useful to find somebody's favourite color. Use sparingly and only when literally someone's favourite color is requested."),
        StructuredTool.from_function(name='Search_EPFL_News', func=search_news, description="Useful to fetch news articles from EPFL. Use sparingly and only when literally news are requested."),
    ]

    # def search_nodes(query: str, limit: int = 5, offset: int = 0):
    #     """Searches the nodes in the knowledge graph that are closest to the query.
    #     Returns at most `limit` nodes and skips the first `offset`nodes."""
    #
    #     results = {
    #         'nodeset': [
    #             {'id': '123456', 'type': 'person', 'name': "Perico de los Palotes", 'url': 'https://graphsearch.epfl.ch/person/123456', 'secret': 'hahahaha'},
    #             {'id': '658789', 'type': 'concept', 'name': "Perico", 'url': 'https://graphsearch.epfl.ch/concept/658789', 'secret': '1234567890'},
    #             {'id': 'dlsaj29r', 'type': 'lecture', 'name': "The Architectural Style of Le Perroquet", 'url': 'https://graphsearch.epfl.ch/lecture/dlsaj29r', 'secret': 'aaa'},
    #             {'id': 'dkalfj99', 'type': 'course', 'name': "Bird breeding", 'url': 'https://graphsearch.epfl.ch/course/dkalfj99', 'secret': '.-.-.'},
    #         ],
    #         'operation': """Nodes related to the Concept "Parrot".""",
    #         'total_node_count': 234
    #     }
    #
    #     return results
    #
    # tools = [StructuredTool.from_function(search_nodes)]

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
    model = (lambda messages: [SystemMessage(content=system_messages['agent'])] + messages) | model

    # Instantiate ToolExecutor that will be used in the 'tools' state
    tool_executor = ToolExecutor(tools)

    ################################################################

    # Define the function that will run in the 'agent' node
    def call_model(state: State, config: RunnableConfig):
        messages = state['messages']
        response = model.invoke(messages, config)

        return {'messages': [response]}

    ################################################################

    # Define the function that will run in the 'agent' node
    def call_tools(state: State, config: RunnableConfig):
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
        messages = state['messages']
        last_message = messages[-1]

        # If there are tool calls, go to the 'tools' node
        if last_message.tool_calls:
            return 'tools'

        # Otherwise finish execution
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


################################################################

def send_message(conversation_id, prompt):
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


################################################################

# Create agent
agent = create_agent()

if __name__ == '__main__':
    conversation_id = '1234'

    prompt = "Hey, I'm Aitor! Are there any news on the new president from EPFL?"
    print(send_message(conversation_id, prompt)['message'])

    prompt = "What about exercises on differential equations?"
    print(send_message(conversation_id, prompt)['message'])

    prompt = "Did I tell you my name?"
    print(send_message(conversation_id, prompt)['message'])

    conversation_id = '123456'

    prompt = "Did I tell you my name?"
    print(send_message(conversation_id, prompt)['message'])
