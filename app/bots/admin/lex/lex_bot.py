from app.bots.admin.admin_bot import AdminBot


CATEGORIES = {
    'greeting': {'description': "The user is just greeting the assistant or similar.", 'tool_choice': None},
    'recruiting': {'description': "Requests about recruitment at EPFL, including PhD students, postdocs, researchers or any other EPFL staff member.", 'tool_choice': 'any'},
    'contract-management': {'description': "Requests about the EPFL work contract for all kind of staff members.", 'tool_choice': 'any'},
    'internal-processes': {'description': "Requests about internal processes at EPFL, like mandatory trainings or electing people for management positions.", 'tool_choice': 'any'},
    'equipment': {'description': "Requests about equipment or material at EPFL, like purchasing some piece of equipment for research in a lab or regulations on office material.", 'tool_choice': 'any'},
    'absences': {'description': "Requests about absences at EPFL, including paid leaves (holidays, medical leaves, maternity or paternity leaves, accidents, etc.) unpaid leaves, teleworking or other absences.", 'tool_choice': 'any'},
    'epfl-presidency': {'description': "Explicit requests about the presidency of EPFL.", 'tool_choice': 'any'},
    'epfl-vice-presidencies': {'description': "Explicit requests about the vice-presidencies of EPFL.", 'tool_choice': 'any'},
    'unrelated': {'description': "The user's request is completely unrelated to EPFL Polylex or EPFL laws and regulations.", 'tool_choice': None},
}


class LexBot(AdminBot):
    name = 'lex'
    index = 'lex'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'graph-rag-lex']

    tool_name = 'search_lex'

    CATEGORIES = CATEGORIES
