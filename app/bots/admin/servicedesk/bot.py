from app.bots.admin.bot import AdminBot


CATEGORIES = {
    'greeting': {'description': "The user is just greeting the assistant or similar.", 'force_tools': False},
    'epfl': {'description': "Requests about EPFL IT services and infrastructure.", 'force_tools': True},
    'public': {'description': "Requests about public-facing IT services.", 'force_tools': True},
    'finances': {'description': "Requests about financial IT tools or processes.", 'force_tools': True},
    'research': {'description': "Requests about research IT support.", 'force_tools': True},
    'human-resources': {'description': "Requests about HR IT tools or processes.", 'force_tools': True},
    'servicedesk': {'description': "Requests about Service Desk procedures or support.", 'force_tools': True},
    'unrelated': {'description': "The user's request is completely unrelated to EPFL IT or Service Desk topics.", 'force_tools': False},
}


class ServicedeskBot(AdminBot):
    name = 'servicedesk'
    index = 'servicedesk'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'graph-rag-servicedesk', 'SI-ServiceDesk-Niv1']

    tool_name = 'search_servicedesk'
    tool_description = "Searches EPFL's IT Service Desk knowledge base (guides, support articles, best practices on IT activities) with the given query. Returns matching document chunks."

    CATEGORIES = CATEGORIES

    @property
    def bot_introduction(self) -> str:
        return (
            "You are the assistant of EPFL Graph, the project of the knowledge graph of EPFL. "
            "You also have access to the knowledge bases of EPFL Service Desk, with guides, support and best practices "
            "on various topics about IT activities at EPFL. "
            "Your task is to answer questions from EPFL students, researchers or staff members."
        )

