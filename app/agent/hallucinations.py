import regex as re

from app.agent.tool_interactions import get_tool_interactions


def extract_dict_links(d):
    if isinstance(d, list):
        link_lists = [extract_dict_links(x) for x in d]
        return [link for link_list in link_lists for link in link_list]

    if isinstance(d, dict):
        if 'url' in d:
            links = [d['url']]
        else:
            links = []

        link_lists = [extract_dict_links(d[x]) for x in d if x != 'url']
        links.extend([link for link_list in link_lists for link in link_list])

        return links

    return []


def extract_message_links(content):
    group_1 = r'([^][]+)'                       # Group 1: One or more characters other than '[' or ']'
    text_pattern = fr'\[{group_1}\]'            # Text pattern: '[' + Group 1 + ']'

    group_3 = r'((?:[^()]+|(?2))+)'             # Group 3: One or more characters, either different from '[' and ']', or Group 2
    group_2 = fr'(\({group_3}\))'               # Group 2: '(' + Group 3 + ')'
    url_pattern = group_2

    link_pattern = text_pattern + url_pattern   # Concatenate both
    link_regex = re.compile(link_pattern)

    message_links = [url for text, _, url in link_regex.findall(content)]

    return message_links


def get_hallucinated_links(thread_id, messages):
    # Split messages into last and past messages, and keep only AI past messages
    last_message = messages[-1]
    past_messages = messages[:-1]

    # Last message links are candidates for being hallucinated
    last_message_links = set(extract_message_links(last_message.content))
    print('[POST-MODEL]', f"Found {len(last_message_links)} links in last LLM message")

    # If there are no links there can't be hallucinated links, we return
    if not last_message_links:
        return []

    # Links in past messages are considered valid (we have checked them already at some point)
    past_message_links = set()
    for past_message in past_messages:
        past_message_links |= set(extract_message_links(past_message.content))
    print('[POST-MODEL]', f"Found {len(past_message_links)} links in previous LLM messages")

    # Extract tool links
    tool_interactions = get_tool_interactions(thread_id)
    tool_links = set(extract_dict_links(tool_interactions))
    print('[POST-MODEL]', f"Found {len(tool_links)} links in tool interactions")

    # Exclude known exceptions
    exception_links = set(
        "https://www.epfl.ch/about/respect/trust-and-support-network/"
    )

    # Valid links are tool links, past message links or exceptions
    valid_links = tool_links | past_message_links | exception_links

    # Return links from the last message which are not valid
    return list(last_message_links - valid_links)
