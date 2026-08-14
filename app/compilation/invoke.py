import logging
from typing import TYPE_CHECKING, Any, Mapping, TypeVar

from pydantic import BaseModel

from app.compilation.base import MessageCompiler
from app.llms.utils import generate_structured_response

if TYPE_CHECKING:
    from app.bots.base import Bot

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


async def structured_call(
    bot: "Bot",
    compiler: type[MessageCompiler],
    state: Mapping[str, Any],
    fallback: T,
) -> T:
    """Compile the call, run it, and return the parsed result — or `fallback` if anything goes wrong.

    Compilation stays outside the call's own error handling: a template or
    context bug is a programmer error and should surface, not degrade into a
    silent fallback on every turn.
    """
    messages = compiler.compile(bot, state)
    model = bot.model_for(compiler.config.model_choice)

    result = await generate_structured_response(model, messages, compiler.config.output_schema)
    if result is None:
        logger.warning("Structured %s call produced nothing; falling back to defaults", compiler.config.task)
        return fallback

    return result
