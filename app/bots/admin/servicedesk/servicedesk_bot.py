from app.bots.admin.admin_bot import AdminBot

CATEGORIES = {
    "greeting": {"description": "The user is just greeting the assistant or similar.", "tool_choice": None},
    "epfl": {"description": "Requests about EPFL IT services and infrastructure.", "tool_choice": "any"},
    "public": {"description": "Requests about public-facing IT services.", "tool_choice": "any"},
    "finances": {"description": "Requests about financial IT tools or processes.", "tool_choice": "any"},
    "research": {"description": "Requests about research IT support.", "tool_choice": "any"},
    "human-resources": {"description": "Requests about HR IT tools or processes.", "tool_choice": "any"},
    "servicedesk": {"description": "Requests about Service Desk procedures or support.", "tool_choice": "any"},
    "unrelated": {
        "description": "The user's request is completely unrelated to EPFL IT or Service Desk topics.",
        "tool_choice": None,
    },
}


class ServicedeskBot(AdminBot):
    name = "servicedesk"
    index = "servicedesk"
    groups = ["graph-chatbot-admins", "graph-rag-vip", "graph-rag-servicedesk", "SI-ServiceDesk-Niv1"]

    tool_name = "search_servicedesk"

    CATEGORIES = CATEGORIES
