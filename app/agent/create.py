from typing import Optional

from langchain_core.messages import (
    SystemMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain.tools import StructuredTool

from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt.tool_node import ToolNode
from langgraph.types import Command

from app.agent.tools import search_nodes, search_exercises, search_news, search_plan, get_orgchart


################################################################
# State class for the agent graph                              #
################################################################

class State(MessagesState):
    """
    Class that represents a state on the graph. It holds:
        * A list of 'messages' (as it subclasses from MessagesState)
        * Other variables that keep track of the status of the execution
    """

    category: Optional[str]
    tools_queue: Optional[list[str]]


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

    def build_tools(integration):
        tool_map = {
            'search_nodes': search_nodes,
            'search_exercises': search_exercises,
            'search_news': search_news,
            'search_plan': search_plan,
            'get_orgchart': get_orgchart,
        }

        tools = []

        # Common tools
        for tool_name in integration.available_tools:
            if tool_name in tool_map:
                tools.append(StructuredTool.from_function(name=tool_name, coroutine=tool_map[tool_name]))

        # Integration-specific tools
        tools += integration.build_tools()

        return tools

    ################################################################
    # Classify node                                                #
    ################################################################

    async def classify_node(state: State, config: RunnableConfig):
        # Recover integration config object from agent config
        integration = config.get('configurable', {}).get('integration')

        # Classify request
        request_type = await integration.classify(state['messages'])
        print('[CLASSIFY]', f"Classified conversation as `{request_type}`")

        # Queue tools to be forced according to request_type
        request_type_tools = integration.request_type_tools(request_type)
        update = {'tools_queue': request_type_tools}

        # Add system message with custom instructions for request_type
        request_type_instructions = integration.request_type_instructions(request_type)
        if request_type_instructions:
            update['messages'] = [SystemMessage(content=request_type_instructions)]

        return Command(goto='premodel', update=update)

    ################################################################
    # Custom premodel node                                         #
    ################################################################

    async def premodel_node(state: State, config: RunnableConfig):
        # Recover integration config object from agent config
        integration = config.get('configurable', {}).get('integration')

        # Run the custom premodel function from the integration
        command = await integration.premodel(state['messages'])

        if command:
            return command
        else:
            return Command(goto='model')

    ################################################################
    # Model node                                                   #
    ################################################################

    async def model_node(state: State, config: RunnableConfig):
        # Recover integration config object from agent config
        integration = config.get('configurable', {}).get('integration')

        # Build tool functions to pass to the model based on those available to the integration
        tools = build_tools(integration)

        # Force tool call if there is any in the queue
        tools_queue = state['tools_queue']
        if tools_queue:
            tool_name = tools_queue.pop(0)  # Returns first element and removes it from tools_queue

            # Instantiate chat model (for tool calling always cheaper model)
            model_with_tools = integration.light_model.bind_tools(tools, tool_choice=tool_name)

            print('[MODEL]', f"Calling LLM forcing tool call `{tool_name}`")
        else:
            # Instantiate chat model (for actual response the model from the integration)
            model_with_tools = integration.model.bind_tools(tools)

            print('[MODEL]', "Calling LLM without forcing any tool call")

        # Generate new ai message
        messages = state['messages']
        messages_with_system_prompt = [SystemMessage(content=integration.system_prompt)] + messages
        ai_message = await model_with_tools.ainvoke(messages_with_system_prompt, config)

        # Hand over to 'tools' if the ai message contains tool calls or proceed to 'check' otherwise
        if ai_message.tool_calls:
            print(ai_message)
            return Command(goto='tools', update={'messages': [ai_message], 'tools_queue': tools_queue})
        else:
            return Command(goto='postmodel', update={'messages': [ai_message], 'tools_queue': tools_queue})

    ################################################################
    # Tools node                                                   #
    ################################################################

    async def tools_node(state: State, config: RunnableConfig):
        # Recover integration config object from agent config
        integration = config.get('configurable', {}).get('integration')

        print('[TOOL]', "Building tools")

        # Build tool functions to pass to the model based on those available to the integration
        tools = build_tools(integration)

        print('[TOOL]', "Fixing issues")

        ################################################################

        # Fix some known issues if needed
        for i in range(len(state['messages'][-1].tool_calls)):
            # Fix missing tool call ids in some cases for some models (c.f. https://github.com/langchain-ai/langgraph/issues/4717)
            if not state['messages'][-1].tool_calls[i]['id']:
                print('[TOOL]', "Missing tool call id. Fixing it manually with a random string.")
                import secrets
                random_hex_string = secrets.token_hex(32 // 2)
                state['messages'][-1].tool_calls[i]['id'] = f"chatcmpl-tool-{random_hex_string}"

            # Fix tool name being a repetition of a tool name (e.g. 'search_lexsearch_lexsearch_lex' instead of 'search_lex')
            tool_names = [tool.name for tool in tools]
            if state['messages'][-1].tool_calls[i]['name'] not in tool_names:
                for tool_name in tool_names:
                    if tool_name in state['messages'][-1].tool_calls[i]['name']:
                        print('[TOOL]', f"Fixing repeated tool call name {state['messages'][-1].tool_calls[i]['name']}.")
                        state['messages'][-1].tool_calls[i]['name'] = tool_name
                        break

        ################################################################

        print('[TOOL]', "Executing tool calls")

        # Execute all tool calls in the last message
        result = await ToolNode(tools).ainvoke(state)
        tool_messages = result['messages']

        print('[TOOL]', "Done, handing to model")

        return Command(goto='model', update={'messages': tool_messages})

    ################################################################
    # Custom postmodel node                                        #
    ################################################################

    async def postmodel_node(state: State, config: RunnableConfig):
        # Recover integration config object from agent config
        integration = config.get('configurable', {}).get('integration')

        # Run the custom postmodel function from the integration
        await integration.postmodel(state['messages'])

        return Command(goto=END)

    ################################################################
    # State graph                                                  #
    ################################################################

    # Define a new graph
    workflow = StateGraph(State)

    # Define the nodes of the graph
    workflow.add_node('classify', classify_node)
    workflow.add_node('premodel', premodel_node)
    workflow.add_node('model', model_node)
    workflow.add_node('tools', tools_node)
    workflow.add_node('postmodel', postmodel_node)

    # Define the entry point of the graph
    workflow.set_entry_point('classify')

    # Compile the StateGraph into a Langchain Runnable, so it can be invoked, streamed, batched and run asynchronously
    agent = workflow.compile()
    agent.step_timeout = 600

    return agent
