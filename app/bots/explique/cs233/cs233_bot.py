from app.bots.explique.explique_bot import ExpliqueBot


class CS233Bot(ExpliqueBot):
    """Explique tutor for CS-233 Introduction to Machine Learning."""

    name = "explique-cs233"
    index = "course_cs233"
    groups = ["graph-chatbot-admins", "graph-rag-vip", "explique-admins"]
