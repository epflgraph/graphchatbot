from app.bots.explique.compilers.retrieve import RetrieveCompiler
from app.bots.explique.grade.compilers.base import GradeDialogTextContext, GradedTurnsCompiler


class GradeRetrieveCompiler(GradedTurnsCompiler, RetrieveCompiler):
    """The tutor's retrieval, searching from the graders' view of the conversation."""

    context_class = GradeDialogTextContext
