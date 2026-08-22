from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.train.compilers.base import ExpliqueCompiler, ExpliqueTask
from app.bots.explique.train.transcript import last_student_turn, prior_turns
from app.bots.nodes.detect_language import LanguageDetection
from app.compilation.base import MessageCompilerConfig, ModelChoice, PromptContext


class LanguageDetectorContext(PromptContext):
    """The turn to infer its language from, and the required prior
    conversation when that turn is too thin to disambiguate."""

    last_student_turn: str
    prior_turns: str


class LanguageDetectorCompiler(ExpliqueCompiler):
    """Detects the student's language from their latest turn."""

    # Enough context to resolve an "ok" or an emoji, short enough to stay cheap.
    PRIOR_TURNS = 9

    context_class = LanguageDetectorContext

    config = MessageCompilerConfig(
        task=ExpliqueTask.DETECT_LANGUAGE,
        model_choice=ModelChoice.LIGHT,
        system_template="detect-language-sys.md",
        user_template="detect-language-usr.md",
        output_schema=LanguageDetection,
    )

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {
            "last_student_turn": last_student_turn(state["messages"]),
            "prior_turns": prior_turns(state["messages"], cls.PRIOR_TURNS),
        }
