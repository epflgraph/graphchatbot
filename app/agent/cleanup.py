from langchain_core.messages import (
    AIMessage,
    ToolMessage,
)


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

