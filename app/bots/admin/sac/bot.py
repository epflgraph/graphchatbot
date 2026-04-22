from app.bots.admin.bot import AdminBot


CATEGORIES = {
    'greeting': {'description': "The user is just greeting the assistant or similar.", 'force_tools': False},
    'guidelines': {'description': "Requests about guidelines and regulations.", 'force_tools': True},
    'studies': {'description': "Requests about studies.", 'force_tools': True},
    'other': {'description': "Other requests related to Service académique.", 'force_tools': True},
    'unrelated': {'description': "The user's request is completely unrelated to Service académique or EPFL studies.", 'force_tools': False},
}


class SacBot(AdminBot):
    name = 'sac'
    index = 'sac'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'graph-rag-sac']

    tool_name = 'search_sac'
    tool_description = "Searches EPFL's Service académique documents (admissions, registrations, record-keeping, resource management for all training courses) with the given query. Returns matching document chunks."

    CATEGORIES = CATEGORIES

