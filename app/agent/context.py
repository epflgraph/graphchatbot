def generate_context(message, tool_interactions):
    message_nodes = []

    # Keep only nodes and links that appear in the message
    for tool_interaction in tool_interactions:
        for node in tool_interaction['tool_response']:
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
