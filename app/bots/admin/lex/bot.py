from langchain.tools import tool

from app.agent.tools import get_orgchart, search_news
from app.bots.admin.bot import AdminBot
from app.bots.prompts import general_considerations
from app.interfaces.graphai import GraphAIClient


CATEGORIES = {
    'greeting': {'description': "The user is just greeting the assistant or similar.", 'force_tools': False},
    'recruiting': {'description': "Requests about recruitment at EPFL, including PhD students, postdocs, researchers or any other EPFL staff member.", 'force_tools': True},
    'contract-management': {'description': "Requests about the EPFL work contract for all kind of staff members.", 'force_tools': True},
    'internal-processes': {'description': "Requests about internal processes at EPFL, like mandatory trainings or electing people for management positions.", 'force_tools': True},
    'equipment': {'description': "Requests about equipment or material at EPFL, like purchasing some piece of equipment for research in a lab or regulations on office material.", 'force_tools': True},
    'absences': {'description': "Requests about absences at EPFL, including paid leaves (holidays, medical leaves, maternity or paternity leaves, accidents, etc.) unpaid leaves, teleworking or other absences.", 'force_tools': True},
    'epfl-presidency': {'description': "Explicit requests about the presidency of EPFL.", 'force_tools': True},
    'epfl-vice-presidencies': {'description': "Explicit requests about the vice-presidencies of EPFL.", 'force_tools': True},
}


class LexBot(AdminBot):
    name = 'lex'
    index = 'lex'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'graph-rag-lex']

    CATEGORIES = CATEGORIES

    @property
    def system_prompt(self) -> str:
        return f"""
You are the EPFL Graph Polylex assistant. You have access to the Polylex documents, a compendium of EPFL laws, ordinances, regulations and directives. Your task is to answer questions from EPFL students, researchers or staff members.

# Format
{self._admin_format}

# General considerations
{self._admin_behavior}
{general_considerations()}"""

    _admin_format = """\
* Lay out urls as Markdown links.
* The result should be a mix between text and Markdown links in a Wikipedia fashion.
* Mix in the relevant resources from the tools in your response as Markdown links in-between the explanation, instead of everything at the end.
* Include at least 5 inline links to resources in your answer.
* Do not use words or phrases that express doubt or provide a subjective opinion."""

    _admin_behavior = """\
* Be proactive and helpful when you answer: Give specific suggestions about what you can do next in relation with your response.
* Never alter the information from the source documents. Copy fields exactly as they are.
* Use Markdown links often. As their text, avoid placeholder words like "here" or "this link".
* If the tools cannot provide an answer to the request, or they return an error, then just apologize and ask the user to rephrase their query.
* If the request is subjective, do not use any tool. Instead, ask the user to rephrase it in an objective way."""

    async def search_lex(self, query: str):
        """
        Performs a search in EPFL's Polylex documents (Electronic compendium of EPFL laws, ordinances, regulations and directives) with the given `query`.
        Returns a list of the document chunks that best match the query.
        """
        print("[LEX TOOL]", f"Called `search_lex` with query=`{query}`")
        results = await GraphAIClient().rag_retrieve(index=self.index, texts=[query])
        print("[LEX TOOL]", f"Retrieved {len(results)} chunks.")
        return results

    def build_tools(self) -> list:
        return [
            tool("search_lex")(self.search_lex),
            tool("get_orgchart")(get_orgchart),
            tool("search_news")(search_news),
        ]
