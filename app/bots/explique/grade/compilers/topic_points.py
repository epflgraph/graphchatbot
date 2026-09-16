from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.grade.compilers.base import GradeCompiler, GradeContext, GradeTask
from app.bots.explique.grade.models import TopicPoints
from app.compilation.base import MessageCompilerConfig, ModelChoice


class TopicPointsContext(GradeContext):
    topic_material: str


class SourcedTopicPointsCompiler(GradeCompiler):
    """Derives a topic's breakdown in points from the course material that covers it."""

    config = MessageCompilerConfig(
        task=GradeTask.DERIVE_POINTS,
        system_template="topic-points-sys.md",
        user_template="topic-points-usr.md",
        model_choice=ModelChoice.LIGHT,
        output_schema=TopicPoints,
    )
    context_class = TopicPointsContext

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"topic_material": state["topic_material"]}


class UnsourcedTopicPointsCompiler(GradeCompiler):
    """Last resort: the same job as SourcedTopicPointsCompiler, but with no source material."""

    config = MessageCompilerConfig(
        task=GradeTask.DERIVE_POINTS,
        system_template="topic-points-unsourced-sys.md",
        user_template="topic-points-usr.md",
        model_choice=ModelChoice.LIGHT,
        output_schema=TopicPoints,
    )
    context_class = GradeContext
