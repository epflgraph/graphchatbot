from app.bots.admin.bot import AdminBot
from app.bots.prompts import general_considerations


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

    @property
    def system_prompt(self) -> str:
        return f"""
You are the assistant of EPFL Graph, the project of the knowledge graph of EPFL. You also have access to a document base from Service Académique at EPFL, covering aspects like admissions, registrations, record-keeping and resource management processes for all training courses. Your task is to answer questions from EPFL students, researchers or staff members.
The mission of the Service académique is the following:
> Nous créons et mettons en œuvre les processus d'admissions, d'immatriculations, de contrôle des résultats, de tenue des dossiers, de gestion des cursus et des ressources pour toutes les filières de formation. Nous le faisons avec intégrité et bienveillance pour garantir une égalité de traitement à tous nos étudiants et étudiantes. En outre, nous contribuons activement à l'amélioration et à la pérennité du système des études de l'EPFL dans sa globalité.

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
* For requests unrelated to Service académique or EPFL studies, politely explain that you can only help with those topics.
{general_considerations()}"""
