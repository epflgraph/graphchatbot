from app.compilation.base import Task


class BotTask(Task):
    CLASSIFY = "classify"
    RETRIEVE = "retrieve"
    RESPOND = "respond"
