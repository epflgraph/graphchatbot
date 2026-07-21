from app.bots.admin.admin_bot import AdminBot


class PlasmaBot(AdminBot):
    name = "plasma"
    index = "course_plasma"
    groups = ["graph-chatbot-admins", "graph-rag-vip", "graph-rag-plasma"]
    tool_name = "search_spc"
