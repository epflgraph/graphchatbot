import logging
from typing import TYPE_CHECKING, Any, Mapping, TypeVar

from pydantic import BaseModel

from app.bots.languages import no_answer
from app.compilation.base import MessageCompiler
from app.llms.utils import flatten_content, generate_response, generate_structured_response

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


async def text_call(
    bot: "Bot",
    compiler: type[MessageCompiler],
    state: Mapping[str, Any],
    tags: tuple[str, ...] = (),
) -> str:
    """Compile the call, run it, and return the model's plain text response, or the
    canned `NO_ANSWER` if anything goes wrong. `tags` reach the client as LangChain run tags.

    Unlike `structured_call` there is no caller-supplied fallback: this is the
    last call of a turn, so nothing downstream can recover it and the student
    reads whatever comes back from here.
    """
    messages = compiler.compile(bot, state)
    model = bot.model_for(compiler.config.model_choice).with_config(tags=list(tags))

    message = await generate_response(model, messages)

    response = flatten_content(message.content) if message is not None else ""
    if not response.strip():
        logger.warning("Text %s call produced nothing; falling back to NO_ANSWER", compiler.config.task)
        return no_answer(state.get("lang_code"))

    return response
