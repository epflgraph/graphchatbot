import logging
from typing import TYPE_CHECKING, Any, Callable, Mapping, TypeVar

from langchain_core.callbacks import AsyncCallbackHandler
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


class TextStreamCallbackHandler(AsyncCallbackHandler):
    """Hands each token of a streamed call to `stream_writer` as it arrives."""

    raise_error = True

    def __init__(self, stream_writer: Callable[[str], None]):
        self.stream_writer = stream_writer

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self.stream_writer(token)


async def text_call(
    bot: "Bot",
    compiler: type[MessageCompiler],
    state: Mapping[str, Any],
    tags: tuple[str, ...] = (),
    fallback: str | None = None,
    stream_writer: Callable[[str], None] | None = None,
) -> str:
    """Compile the call, run it, and return the model's plain text response, or `fallback` if anything goes wrong.
    - `tags` reach the client as LangChain run tags.
    - `fallback` defaults to a canned apology, in the language of the turn.
    - `stream_writer` streams the call: it is handed each token as it arrives.
    """
    messages = compiler.compile(bot, state)
    model = bot.model_for(compiler.config.model_choice).with_config(tags=list(tags))
    if stream_writer is not None:
        model = model.bind(stream=True).with_config(callbacks=[TextStreamCallbackHandler(stream_writer)])

    message = await generate_response(model, messages)

    response = flatten_content(message.content) if message is not None else ""
    if not response.strip():
        logger.warning("Text %s call produced nothing; using fallback response", compiler.config.task)
        return no_answer(bot.prompt_search_path, state.get("lang_code")) if fallback is None else fallback

    return response
