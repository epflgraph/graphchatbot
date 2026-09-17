from app.bots.explique.grade.explique_bot import ExpliqueGradeBot


class DemoGradeBot(ExpliqueGradeBot):
    name = "Explique"
    index = "course_swissunidemo"
    course_id = 19162
    groups = ["graph-chatbot-admins", "graph-rag-vip", "explique-admins"]
