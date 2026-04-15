import secrets

from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.types import Command


def make_tools_node(tools: list, back_to: str = 'model'):
    """
    Returns a tools node that executes all tool calls in the last message.

    Args:
        tools:   list of tool functions available to the model.
        back_to: name of the node to route to after tool execution.
    """

    async def tools_node(state, runtime: Runtime) -> Command:
        tool_calls = state['messages'][-1].tool_calls
        tool_names = [t.name for t in tools]

        for i, tc in enumerate(tool_calls):
            # Fix missing tool call ids (https://github.com/langchain-ai/langgraph/issues/4717)
            if not tc['id']:
                print('[TOOLS]', "Missing tool call id, fixing with random string.")
                state['messages'][-1].tool_calls[i]['id'] = f"chatcmpl-tool-{secrets.token_hex(16)}"

            # Fix tool name being repeated (e.g. 'search_lexsearch_lex' → 'search_lex')
            if tc['name'] not in tool_names:
                for name in tool_names:
                    if name in tc['name']:
                        print('[TOOLS]', f"Fixing repeated tool name `{tc['name']}` → `{name}`.")
                        state['messages'][-1].tool_calls[i]['name'] = name
                        break

        print('[TOOLS]', f"Executing {len(tool_calls)} tool call(s) in parallel")
        result = await ToolNode(tools).ainvoke(state)

        return Command(goto=back_to, update={'messages': result['messages']})

    return tools_node
