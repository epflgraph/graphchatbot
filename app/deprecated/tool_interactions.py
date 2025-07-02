tool_interactions = {}


def append_tool_interaction(thread_id, tool_interaction):
    tool_interactions.setdefault(thread_id, [])
    tool_interactions[thread_id].append(tool_interaction)


def get_tool_interactions(thread_id):
    return tool_interactions.get(thread_id, [])


def clear_tool_interactions(thread_id):
    tool_interactions[thread_id] = []

