from app.bots.explique.explique_bot import ExpliqueBot


class CS112GBot(ExpliqueBot):
    """Explique tutor for CS-112(g) Object Oriented Programming."""

    name = "explique-cs112g"
    index = "course_cs112g"
    groups = ["graph-chatbot-admins", "graph-rag-vip", "explique-admins"]
