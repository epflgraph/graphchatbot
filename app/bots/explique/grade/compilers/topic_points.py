from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.grade.compilers.base import GradeCompiler, GradeContext, GradeTask
from app.bots.explique.grade.models import ExtractedPoints, TopicPoints
from app.compilation.base import MessageCompilerConfig, ModelChoice


class GradeTopicPointsContext(GradeContext):
    topic_material: str


class GradeExtractPointsContext(GradeContext):
    stringified_points: str


class GradeSourcedTopicPointsCompiler(GradeCompiler):
    """Derives a topic's breakdown in points from the course material that covers it."""

    config = MessageCompilerConfig(
        task=GradeTask.DERIVE_POINTS,
        system_template="topic-points-sys.md",
        user_template="topic-points-usr.md",
        model_choice=ModelChoice.FAST,
        output_schema=TopicPoints,
    )
    context_class = GradeTopicPointsContext

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"topic_material": state["topic_material"]}


class GradeUnsourcedTopicPointsCompiler(GradeCompiler):
    """Last resort: the same job as GradeSourcedTopicPointsCompiler, but with no source material."""

    config = MessageCompilerConfig(
        task=GradeTask.DERIVE_POINTS,
        system_template="topic-points-unsourced-sys.md",
        user_template="topic-points-usr.md",
        model_choice=ModelChoice.FAST,
        output_schema=TopicPoints,
    )
    context_class = GradeContext


class GradeExtractPointsCompiler(GradeCompiler):
    """Turns a professor's stringified points for a topic into a list, verbatim."""

    config = MessageCompilerConfig(
        task=GradeTask.EXTRACT_POINTS,
        system_template="extract-points-sys.md",
        user_template="extract-points-usr.md",
        model_choice=ModelChoice.FAST,
        output_schema=ExtractedPoints,
    )
    context_class = GradeExtractPointsContext

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"stringified_points": state["stringified_points"]}
