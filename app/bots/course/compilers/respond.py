from typing import TYPE_CHECKING, Any, Mapping

from app.bots.compilers.respond import ResponseCompiler, ResponseContext

if TYPE_CHECKING:
    from app.bots.base import Bot


class GroundedResponseContext(ResponseContext):
    """The conversation, plus the language to reply in; None when none could be read."""

    lang_code: str | None


class GroundedResponseCompiler(ResponseCompiler):
    """The reply, grounded in the turns that retrieved its sources.

    The conversation is kept whole: the `search_course_material` calls and
    their results remain real turns in it, so the reply is written right
    after the material it cites.
    """

    context_class = GroundedResponseContext

    config = ResponseCompiler.config.model_copy(update={"system_template": "respond-sys.md"})

    @classmethod
    def context_fields(cls, bot: "Bot", state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"lang_code": state.get("lang_code")}
