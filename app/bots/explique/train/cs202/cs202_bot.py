from app.bots.explique.train.explique_bot import ExpliqueBot


class CS202Bot(ExpliqueBot):
    """Explique tutor for CS-202 Computer Systems."""

    name = "explique-cs202"
    index = "course_cs202"
    groups = ["graph-chatbot-admins", "graph-rag-vip", "explique-admins"]
