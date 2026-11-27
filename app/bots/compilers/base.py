from app.compilation.base import Task


class BotTask(Task):
    DETECT_LANGUAGE = "detect-language"
    CLASSIFY = "classify"
    RETRIEVE = "retrieve"
    RESPOND = "respond"
