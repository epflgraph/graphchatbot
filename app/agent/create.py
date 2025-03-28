from typing import Optional
import json

from langchain_core.messages import (
    SystemMessage,
    AIMessage,
    RemoveMessage,
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
from app.agent.tool_interactions import append_tool_interaction
from app.agent.tools import search_nodes, search_exercises, search_news, search_plan, get_orgchart, search_integration
from app.agent.classify import classify_conversation, get_category_details
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

    integration: Optional[str]
    use_tools: Optional[bool]
    style: Optional[str]
    style_prompt: Optional[str]
    ####
    category: Optional[str]
    tools_queue: Optional[list[str]]
    hallucinated_links: Optional[list[str]]


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

    def get_tools(state):
        if state['use_tools']:
            tools = [
                StructuredTool.from_function(name='search_nodes', func=search_nodes),
                StructuredTool.from_function(name='search_exercises', func=search_exercises),
                StructuredTool.from_function(name='search_news', func=search_news),
                StructuredTool.from_function(name='search_plan', func=search_plan),
                StructuredTool.from_function(name='get_orgchart', func=get_orgchart),
            ]
        else:
            tools = []

        if state['integration'] and state['integration'] != 'base':
            tools.append(StructuredTool.from_function(name='search_integration', func=search_integration))

        return tools

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

    def supervisor_node(state: State, config: RunnableConfig):
        integrations = config.get('configurable', {}).get('integrations', [])
        use_tools = config.get('configurable', {}).get('use_tools', True)
        style = config.get('configurable', {}).get('style')
        style_prompt = config.get('configurable', {}).get('style_prompt')

        print('[CLASSIFY]', f"Params: integrations {integrations}, use_tools {use_tools}, style `{style}`, style_prompt `{style_prompt}`")

        if integrations:
            # Pick the first integration TODO: Allow for multiple integrations (if that's what we want to do)
            integration = integrations[0]
            # If the integration has an associated tool, queue it so that we force it later
            tools_queue = ['search_integration']
        else:
            integration = 'base'
            # Base integration does not have a fixed tool to be forced
            tools_queue = []

        # Normalise some of the integration names TODO Coordinate with Thijs and Ramtin so that this parameter is exactly the index name
        if integration == 'service-desk':
            integration = 'servicedesk'

        update = {
            'integration': integration,
            'use_tools': use_tools,
            'style': style,
            'style_prompt': style_prompt,
            'tools_queue': tools_queue,
        }

        return Command(goto='classify', update=update)

    ################################################################
    # Classify node                                                #
    ################################################################

    def classify_node(state: State):
        messages = state['messages']
        integration = state['integration']
        use_tools = state['use_tools']
        style = state['style']
        style_prompt = state['style_prompt']

        # Classify conversation
        category = classify_conversation(messages, integration)
        print('[CLASSIFY]', f"Classified conversation as `{category}`")

        # Get category details and plan category-specific actions (system prompt, tools, etc.)
        category_details = get_category_details(category, integration, style, style_prompt)

        update = {'category': category}

        if 'system_prompt' in category_details:
            update['messages'] = [SystemMessage(content=category_details['system_prompt'])]

        if use_tools and 'tools' in category_details:
            update['tools_queue'] = state['tools_queue'] + category_details['tools']

        return Command(goto='model', update=update)

    ################################################################
    # Model node                                                   #
    ################################################################

    def model_node(state: State, config: RunnableConfig):
        # Extract the list of messages from conversation history
        messages = state['messages']
        integration = state['integration']
        use_tools = state['use_tools']

        tools = get_tools(state)

        # Force tool call if there is any in the queue
        tools_queue = state['tools_queue']
        if tools_queue:
            tool_name = tools_queue.pop(0)  # Returns first element and removes it from tools_queue
            model_with_tools = model.bind_tools(tools, tool_choice=tool_name)
            print('[MODEL]', f"Calling LLM forcing tool call `{tool_name}`")
        else:
            model_with_tools = model.bind_tools(tools)
            print('[MODEL]', "Calling LLM without forcing any tool call")

        # Generate new ai message
        messages_with_system_prompt = [SystemMessage(content=get_system_prompt(integration, use_tools))] + messages
        ai_message = model_with_tools.invoke(messages_with_system_prompt, config)

        # Hand over to 'tools' if the ai message contains tool calls or proceed to 'check' otherwise
        if ai_message.tool_calls:
            return Command(goto='tools', update={'messages': [ai_message], 'tools_queue': tools_queue})
        else:
            return Command(goto='check', update={'messages': [ai_message], 'tools_queue': tools_queue})

    ################################################################
    # Tools node                                                   #
    ################################################################

    def tools_node(state: State, config: RunnableConfig):
        messages = state['messages']
        last_message = messages[-1]

        # Execute all tool calls in the last message
        tools = get_tools(state)
        tool_messages = ToolNode(tools).invoke(state)['messages']

        # Store tool interactions (unobfuscated)
        tool_calls = last_message.tool_calls
        for tool_call in tool_calls:
            for tool_message in tool_messages:
                if tool_call['id'] == tool_message.tool_call_id:
                    print('[TOOLS]', f"Storing tool call result for `{tool_call['name']}`")

                    if isinstance(tool_message.content, str):
                        try:
                            tool_response = json.loads(tool_message.content)
                        except json.decoder.JSONDecodeError as e:
                            print('[TOOLS]', f"WARNING: Could not parse tool response: {e}. Tool result: {tool_message.content}")
                            tool_response = []
                    else:
                        # Oddly enough, when tool returns empty list, content is not a string '[]' but an actual empty list
                        tool_response = tool_message.content

                    tool_interaction = {'tool_call': tool_call, 'tool_response': tool_response}
                    append_tool_interaction(config['configurable']['thread_id'], tool_interaction)
                    break

        # TODO: Obfuscate result if needed
        pass

        return Command(goto='model', update={'messages': tool_messages})

    ################################################################
    # Check node                                                   #
    ################################################################

    def check_node(state: State, config: RunnableConfig):
        messages = state['messages']

        thread_id = config['configurable']['thread_id']
        ai_sys_messages = [message for message in messages if isinstance(message, AIMessage) or isinstance(message, SystemMessage)]
        hallucinated_links = get_hallucinated_links(thread_id, ai_sys_messages)

        if hallucinated_links:
            print('[CHECK]', f"Found hallucinated links (e.g. {hallucinated_links[0]}). Will return them along with the response.")
        else:
            print('[CHECK]', "Did not find any hallucinated link")

        return Command(goto='cleanup', update={'hallucinated_links': hallucinated_links})

    ################################################################
    # Cleanup node                                                 #
    ################################################################

    def cleanup_node(state: State):
        messages = state['messages']

        # Delete intermediate System messages
        print('[CLEANUP]', "Deleting intermediate system messages")
        messages = clean_system_messages(messages)

        # Delete AI messages with tool requests and their corresponding tool messages
        print('[CLEANUP]', "Deleting tool call requests and responses")
        messages = clean_tool_calls_and_responses(messages)

        # Get a list of ids of messages to remove
        keep_message_ids = [message.id for message in messages]
        remove_message_ids = [message.id for message in state['messages'] if message.id not in keep_message_ids]

        return Command(goto=END, update={'messages': [RemoveMessage(id=remove_message_id) for remove_message_id in remove_message_ids]})

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
    agent.step_timeout = 600

    return agent
