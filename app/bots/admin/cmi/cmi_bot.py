from app.bots.admin.admin_bot import AdminBot


class CMiBot(AdminBot):
    name = 'cmi'
    index = 'course_cmi'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'cmi-chat-bot']
    tool_name = 'search_cmi'
