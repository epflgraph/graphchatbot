from app.bots.explique.grade.explique_bot import ExpliqueGradeBot


class CS233GradeBot(ExpliqueGradeBot):
    """Graded explique exercise for CS-233 Introduction to Machine Learning."""

    name = "explique-cs233"
    index = "course_cs233"
    course_id = 16234
    groups = ["graph-chatbot-admins", "graph-rag-vip", "explique-admins"]
