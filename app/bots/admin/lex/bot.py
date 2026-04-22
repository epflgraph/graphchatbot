from langchain.tools import tool

from app.agent.tools import get_orgchart, search_news
from app.bots.admin.bot import AdminBot


CATEGORIES = {
    'greeting': {'description': "The user is just greeting the assistant or similar.", 'force_tools': False},
    'recruiting': {'description': "Requests about recruitment at EPFL, including PhD students, postdocs, researchers or any other EPFL staff member.", 'force_tools': True},
    'contract-management': {'description': "Requests about the EPFL work contract for all kind of staff members.", 'force_tools': True},
    'internal-processes': {'description': "Requests about internal processes at EPFL, like mandatory trainings or electing people for management positions.", 'force_tools': True},
    'equipment': {'description': "Requests about equipment or material at EPFL, like purchasing some piece of equipment for research in a lab or regulations on office material.", 'force_tools': True},
    'absences': {'description': "Requests about absences at EPFL, including paid leaves (holidays, medical leaves, maternity or paternity leaves, accidents, etc.) unpaid leaves, teleworking or other absences.", 'force_tools': True},
    'epfl-presidency': {'description': "Explicit requests about the presidency of EPFL.", 'force_tools': True},
    'epfl-vice-presidencies': {'description': "Explicit requests about the vice-presidencies of EPFL.", 'force_tools': True},
    'unrelated': {'description': "The user's request is completely unrelated to EPFL Polylex or EPFL laws and regulations.", 'force_tools': False},
}


class LexBot(AdminBot):
    name = 'lex'
    index = 'lex'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'graph-rag-lex']

    tool_name = 'search_lex'
    tool_description = "Performs a search in EPFL's Polylex documents (Electronic compendium of EPFL laws, ordinances, regulations and directives) with the given query. Returns matching document chunks."

    CATEGORIES = CATEGORIES

    def build_tools(self) -> list:
        return [
            tool(self.tool_name, description=self.tool_description)(self._search),
            tool('get_orgchart')(get_orgchart),
            tool('search_news')(search_news),
        ]
