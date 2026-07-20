from app.bots.admin.admin_bot import AdminBot

CATEGORIES = {
    "greeting": {"description": "The user is just greeting the assistant or similar.", "tool_choice": None},
    "guidelines": {"description": "Requests about guidelines and regulations.", "tool_choice": "any"},
    "studies": {"description": "Requests about studies.", "tool_choice": "any"},
    "other": {"description": "Other requests related to Service académique.", "tool_choice": "any"},
    "unrelated": {
        "description": "The user's request is completely unrelated to Service académique or EPFL studies.",
        "tool_choice": None,
    },
}


class SacBot(AdminBot):
    name = "sac"
    index = "sac"
    groups = ["graph-chatbot-admins", "graph-rag-vip", "graph-rag-sac"]

    tool_name = "search_sac"

    CATEGORIES = CATEGORIES
