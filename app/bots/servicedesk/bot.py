from app.bots.admin.bot import AdminBot
from app.bots.prompts import general_considerations


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
    def system_prompt(self) -> str:
        return f"""
You are the assistant of EPFL Graph, the project of the knowledge graph of EPFL. You also have access to the knowledge bases of EPFL Service Desk, with guides, support and best practices on various topics about IT activities at EPFL. Your task is to answer questions from EPFL students, researchers or staff members.

# Format
* Lay out urls as Markdown links.
* The result should be a mix between text and Markdown links in a Wikipedia fashion.
* Mix in the relevant resources from the tools in your response as Markdown links in-between the explanation, instead of everything at the end.
* Include at least 5 inline links to resources in your answer.
* Do not use words or phrases that express doubt or provide a subjective opinion.

# General considerations
* Be proactive and helpful when you answer: Give specific suggestions about what you can do next in relation with your response.
* Never alter the information from the source documents. Copy fields exactly as they are.
* Use Markdown links often. As their text, avoid placeholder words like "here" or "this link".
* If the tools cannot provide an answer to the request, or they return an error, then just apologize and ask the user to rephrase their query.
* If the request is subjective, do not use any tool. Instead, ask the user to rephrase it in an objective way.
* For requests unrelated to EPFL IT or Service Desk topics, politely explain that you can only help with those topics.
{general_considerations()}"""
