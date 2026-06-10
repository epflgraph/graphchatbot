from app.bots.admin.admin_bot import AdminBot


class CMiRestrictedBot(AdminBot):
    name = 'cmi_restricted'
    index = 'course_cmirestricted'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'cmi-chat-bot-private']
    tool_name = 'search_cmi'
