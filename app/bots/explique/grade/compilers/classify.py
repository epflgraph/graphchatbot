from app.bots.explique.compilers.classify import ClassifyCompiler
from app.bots.explique.grade.compilers.base import GradeDialogTextContext, GradedTurnsCompiler


class GradeClassifyCompiler(GradedTurnsCompiler, ClassifyCompiler):
    """The tutor's classifier, reading past the jailbreak turns: an explanation
    sent again after one is an explanation, not a second attempt."""

    context_class = GradeDialogTextContext
