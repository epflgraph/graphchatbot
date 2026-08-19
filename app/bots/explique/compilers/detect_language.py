from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.compilers.base import ExpliqueCompiler, ExpliqueTask
from app.bots.explique.models import LanguageDetection
from app.bots.explique.transcript import last_student_turn, prior_turns
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

    config = MessageCompilerConfig(
        task=ExpliqueTask.DETECT_LANGUAGE,
        model_choice=ModelChoice.LIGHT,
        system_template="detect-language-sys.md",
        user_template="detect-language-usr.md",
        output_schema=LanguageDetection,
    )

    @classmethod
    def build_context(cls, bot: Bot, state: Mapping[str, Any]) -> LanguageDetectorContext:
        return LanguageDetectorContext(
            last_student_turn=last_student_turn(state["messages"]),
            prior_turns=prior_turns(bot.dialog, state["messages"], cls.PRIOR_TURNS),
        )
