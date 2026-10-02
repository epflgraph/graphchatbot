from app.bots.explique.compilers.evaluate import EvaluateCompiler
from app.bots.explique.grade.compilers.base import GradedTurnsCompiler, GradeGroundedDialogContext


class GradeEvaluateCompiler(GradedTurnsCompiler, EvaluateCompiler):
    """The tutor's evaluator, reading the graders' view of the conversation."""

    context_class = GradeGroundedDialogContext
