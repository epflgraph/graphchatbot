from typing import Optional
import json

from langchain_core.messages import (
    SystemMessage,
    AIMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain.tools import StructuredTool
from langchain_openai import ChatOpenAI

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt.tool_node import ToolNode
from langgraph.types import Command

from app.config import config
from app.agent.prompt import get_system_prompt
from app.agent.cache import get_from_cache, set_to_cache
from app.agent.tool_interactions import append_tool_interaction
from app.agent.tools import search_nodes, search_exercises, search_news, search_plan
from app.agent.classify import classify_conversation, get_category_tool, get_category_system_prompt
from app.agent.orgchart import get_orgchart_system_prompt
from app.agent.hallucinations import get_hallucinated_links
from app.agent.cleanup import clean_system_messages, clean_tool_calls_and_responses


################################################################
# State class for the agent graph                              #
################################################################

class State(MessagesState):
    """
    Class that represents a state on the graph. It holds:
        * A list of 'messages' (as it subclasses from MessagesState)
        * Other variables that keep track of the status of the execution
    """

    request_type: Optional[str]
    have_fetched_orgchart: Optional[bool]
    have_used_tools: Optional[bool]
    have_checked_hallucinations: Optional[bool]
    have_cleaned_up: Optional[bool]


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
        StructuredTool.from_function(name='search_plan', func=search_plan),
    ]

    ################################################################
    # Memory                                                       #
    ################################################################

    memory = MemorySaver()

    ################################################################
    # Model                                                        #
    ################################################################

    # Chat model
    model = ChatOpenAI(model='gpt-4o-mini', temperature=0, openai_api_key=config['openai']['api_key'])

    ################################################################
    # Supervisor node                                              #
    ################################################################

    def supervisor_node(state: State):
        # Extract list of messages and last message from state
        messages = state['messages']
        last_message = messages[-1]

        # If request has not been classified, do so
        if state.get('request_type') is None:
            print('[SUPERVISOR]', "Request has not been classified, handing to `classify` state")
            return Command(goto='classify')

        # If the last message is not an AIMessage, we generate one
        if last_message.type != 'ai':
            print('[SUPERVISOR]', f"Last message is {last_message.type}, handing to `model` state")
            return Command(goto='model')

        # If the last message is an AIMessage and there are tool calls, we execute them
        if last_message.tool_calls:
            print('[SUPERVISOR]', "Last message contains some tool calls, handing to `tools` state")
            return Command(goto='tools')

        # If the last message is an AIMessage with no tool calls, we check for hallucinations
        if not state.get('have_checked_hallucinations'):
            print('[SUPERVISOR]', "We need to check for hallucinated links, handing to `check` state")
            return Command(goto='check')

        # If the last message is an AIMessage with no tool calls, and we have checked for hallucinations, we clean up
        if not state.get('have_cleaned_up'):
            print('[SUPERVISOR]', "Need to clean up, handing to `cleanup` state")
            return Command(goto='cleanup')

        print('[SUPERVISOR]', "Finishing execution")
        return Command(goto=END, update={'request_type': None, 'have_used_tools': False, 'have_fetched_orgchart': False, 'have_checked_hallucinations': False, 'have_cleaned_up': False})

    ################################################################
    # Classify node                                                #
    ################################################################

    def classify_node(state: State):
        messages = state['messages']

        category = classify_conversation(messages)
        print('[CLASSIFY]', f"Classified conversation as `{category}`")

        category_system_prompt = get_category_system_prompt(category)

        if category_system_prompt is None:
            return Command(goto='supervisor', update={'request_type': category})
        else:
            return Command(goto='supervisor', update={'messages': [SystemMessage(content=category_system_prompt)], 'request_type': category})

    ################################################################
    # Model node                                                   #
    ################################################################

    def model_node(state: State, config: RunnableConfig):
        # Extract the list of messages from conversation history
        messages = state['messages']
        new_messages = []

        # If it is request about people, and we haven't done it already, add a message with the organizational chart
        have_fetched_orgchart = state.get('have_fetched_orgchart')
        if state['request_type'] == 'people' and not have_fetched_orgchart:
            orgchart_message = SystemMessage(content=get_orgchart_system_prompt())
            messages.append(orgchart_message)
            new_messages.append(orgchart_message)
            have_fetched_orgchart = True

        # Try to fetch response from cache
        response = get_from_cache(messages)

        # Call LLM otherwise
        if response is None:
            print('[MODEL]', "Couldn't find cached response for the given message list, calling LLM")

            # Force tool call if there has not been any
            if state.get('have_used_tools'):
                model_with_tools = model.bind_tools(tools)
            else:
                tool_name = get_category_tool(state.get('request_type'))
                model_with_tools = model.bind_tools(tools, tool_choice=tool_name)

            messages_with_system_prompt = [SystemMessage(content=get_system_prompt())] + messages
            response = model_with_tools.invoke(messages_with_system_prompt, config)
        else:
            print('[MODEL]', "Found cached response for the given message list, skipping LLM")

        # Set result to cache
        set_to_cache(messages, response)

        new_messages.append(response)

        return Command(goto='supervisor', update={'messages': new_messages, 'have_fetched_orgchart': have_fetched_orgchart})

    ################################################################
    # Tools node                                                   #
    ################################################################

    def tools_node(state: State, config: RunnableConfig):
        messages = state['messages']
        last_message = messages[-1]

        # Execute all tool calls in the last message
        tool_messages = ToolNode(tools).invoke([last_message])

        # Store tool interactions (unobfuscated)
        tool_calls = last_message.tool_calls
        for tool_call in tool_calls:
            for tool_message in tool_messages:
                if tool_call['id'] == tool_message.tool_call_id:
                    print('[TOOLS]', f"Storing tool call result for `{tool_call['name']}`")

                    if isinstance(tool_message.content, str):
                        tool_response = json.loads(tool_message.content)
                    else:
                        # Oddly enough, when tool returns empty list, content is not a string '[]' but an actual empty list
                        tool_response = tool_message.content

                    tool_interaction = {'tool_call': tool_call, 'tool_response': tool_response}
                    append_tool_interaction(config['configurable']['thread_id'], tool_interaction)
                    break

        # TODO: Obfuscate result if needed
        pass

        return Command(goto='supervisor', update={'messages': tool_messages, 'have_used_tools': True})

    ################################################################
    # Check node                                                   #
    ################################################################

    def check_node(state: State, config: RunnableConfig):
        messages = state['messages']

        thread_id = config['configurable']['thread_id']
        ai_messages = [message for message in messages if isinstance(message, AIMessage)]
        hallucinated_links = get_hallucinated_links(thread_id, ai_messages)

        if not hallucinated_links:
            print('[CHECK]', "Did not find any hallucinated link")
            return Command(goto='supervisor', update={'have_checked_hallucinations': True})

        # Delete last message because it contains hallucinations
        state['messages'] = state['messages'][:-1]

        # Return new system message warning about the hallucination
        print('[CHECK]', f"Found hallucinated link {hallucinated_links[0]}. Replacing last AI message with system message warning about hallucinations.")
        system_message = SystemMessage(f"Make sure you only include urls present in the results from the tools. For instance, {hallucinated_links[0]} is not a valid url.")
        return Command(goto='supervisor', update={'messages': [system_message], 'have_checked_hallucinations': True})

    ################################################################
    # Cleanup node                                                 #
    ################################################################

    def cleanup_node(state: State):
        # Delete intermediate System messages
        print('[CLEANUP]', "Deleting intermediate system messages")
        state['messages'] = clean_system_messages(state['messages'])

        # Delete AI messages with tool requests and their corresponding tool messages
        print('[CLEANUP]', "Deleting tool call requests and responses")
        state['messages'] = clean_tool_calls_and_responses(state['messages'])

        return Command(goto='supervisor', update={'have_cleaned_up': True})

    ################################################################
    # State graph                                                  #
    ################################################################

    # Define a new graph
    workflow = StateGraph(State)

    # Define the nodes of the graph
    workflow.add_node('supervisor', supervisor_node)
    workflow.add_node('classify', classify_node)
    workflow.add_node('model', model_node)
    workflow.add_node('tools', tools_node)
    workflow.add_node('check', check_node)
    workflow.add_node('cleanup', cleanup_node)

    # Define the entry point of the graph
    workflow.set_entry_point('supervisor')

    # Compile the StateGraph into a Langchain Runnable, so it can be invoked, streamed, batched and run asynchronously
    agent = workflow.compile(checkpointer=memory, debug=False)
    agent.step_timeout = 60

    return agent
