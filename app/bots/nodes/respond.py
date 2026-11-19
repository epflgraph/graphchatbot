import logging
from collections import Counter
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from typing_extensions import Self

from app.bots.artifacts.evaluation import EvaluationContext, evaluate
from app.bots.artifacts.rich_response import (
    LITERAL_LINE_BREAK,
    ResponseBlock,
    ResponseBlockType,
    RichResponse,
    repair_escaping,
)
from app.bots.base import Bot, BotState
from app.bots.languages import no_answer
from app.bots.utils import STATUS_RESPONDING, Source, TurnEvent, announce, stream_text
from app.compilation.base import MessageCompiler
from app.llms.utils import stream_structured_response

logger = logging.getLogger(__name__)

# The model's response, partial while it streams.
RawResponse = dict[str, Any]
# One response block of a `RawResponse`.
RawBlock = dict[str, Any]


class RespondNodeConfig(BaseModel):
    """Settings for a respond node: the prompt, the blocks a response is made of, and where its sources come from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    compiler: type[MessageCompiler]
    # The bot's response, whose `blocks` is the union of the blocks it offers.
    response_schema: type[RichResponse]
    # Collects the sources in the tool results among the messages it is given. The bot passes it in,
    # since only the bot knows the shape its search tool returns.
    retrieved_sources: Callable[[list[BaseMessage]], dict[str, Source]]

    @model_validator(mode="after")
    def _validate_response_schema_types(self) -> Self:
        types = [schema["properties"]["type"]["const"] for schema in self.response_schema.block_schemas()]
        if any(value not in ResponseBlockType for value in types) or len(set(types)) < len(types):
            raise ValueError(
                f"each block {self.response_schema.__name__} offers needs its own ResponseBlockType, not {types!r}"
            )
        return self


class StreamedReply:
    """A reply written onto the stream while the model writes it.

    The model writes its response one block at a time, so a block is complete once the next one starts
    or the response is complete. Text goes out as it grows; any other block waits until it is complete,
    since half a `<details>` or `<video>` shows as raw tags. Each complete block is validated, then
    dropped or written out with its citation numbers, just after any source not cited earlier in the reply.
    """

    def __init__(
        self,
        schema: type[RichResponse],
        sources: dict[str, Source],
        stream_writer: Callable[[TurnEvent], None],
    ):
        self._schema = schema
        self._sources = sources
        self._context = EvaluationContext(urls=frozenset(sources))
        self._stream_writer = stream_writer
        # The text written so far, which is also what the transcript keeps.
        self._text = ""
        # Open WebUI numbers sources in the order they arrive, so a url's number is its place here.
        self._cited_urls = []
        # Open WebUI tells sources apart by title, so a repeated one is numbered.
        self._source_titles = Counter()
        # How many blocks are processed, and the text streamed so far of the one being written.
        self._num_processed_blocks = 0
        self._streamed_block_text = ""

    @property
    def text(self) -> str:
        """Everything the student has read so far."""
        return self._text

    def grow(self, partial: RawResponse) -> None:
        """Process the blocks the model is done with, and write out any new text in the one it is still writing."""
        blocks = partial.get("blocks", [])
        for block in blocks[self._num_processed_blocks : -1]:
            self._process_block(block)
        if blocks:
            self._grow_text(blocks[-1])

    def end(self, response: RawResponse) -> None:
        """Process the blocks still left, now that the model's response is complete."""
        for block in response.get("blocks", [])[self._num_processed_blocks :]:
            self._process_block(block)
        if not self._text:
            logger.warning("The model's response left no block to show")

    async def write_paragraph(self, text: str) -> None:
        """Write `text` after the reply, as a paragraph of its own."""
        if self._text:
            self._write_text(RichResponse.BLOCK_SEPARATOR)
        await stream_text(text, self._write_text)

    def _grow_text(self, block: RawBlock) -> None:
        # What follows a trailing backslash or `\n` decides what it is, so it waits for the next character.
        written = (block.get("content") or "").removesuffix(LITERAL_LINE_BREAK).removesuffix("\\")
        content = repair_escaping(written)
        if block.get("type") == ResponseBlockType.TEXT and content.startswith(self._streamed_block_text):
            self._write_block(content[len(self._streamed_block_text) :])
            self._streamed_block_text = content

    def _process_block(self, data: RawBlock) -> None:
        block = self._validate_block(data)
        if block is not None:
            block = self._cite_sources(block)
            rendered = block.render()
            if rendered.startswith(self._streamed_block_text):
                self._write_block(rendered[len(self._streamed_block_text) :])
            else:
                logger.warning("A %s block's text changed after it was written out; its ending is left out", block.type)
        self._num_processed_blocks += 1
        self._streamed_block_text = ""

    def _validate_block(self, data: RawBlock) -> ResponseBlock | None:
        """The block `data` describes, or None if it fails the schema or its evaluators."""
        try:
            [block] = self._schema.model_validate({"blocks": [data]}).blocks
        except ValidationError:
            logger.warning("Dropped a block that does not match %s", self._schema.__name__, exc_info=True)
            return None
        if tags := evaluate(block, self._context):
            logger.warning("Dropped a %s block, tagged %s", block.type, ", ".join(tags))
            return None
        return block

    def _cite_sources(self, block: ResponseBlock) -> ResponseBlock:
        """Set `block`'s citation numbers, first writing out any source not cited earlier in the reply."""
        response = self._schema(blocks=(block,))
        for url in response.cited_urls(self._context.urls):
            if url not in self._cited_urls:
                self._cited_urls.append(url)
                self._write_source(self._sources[url])
        [block] = response.with_numbered_citations(tuple(self._cited_urls)).blocks
        return block

    def _write_block(self, text: str) -> None:
        """Write more of the current block; each block after the first starts with a blank line."""
        if text:
            if self._text and not self._streamed_block_text:
                self._write_text(RichResponse.BLOCK_SEPARATOR)
            self._write_text(text)

    def _write_source(self, source: Source) -> None:
        self._source_titles[source.title] += 1
        if self._source_titles[source.title] > 1:
            source = replace(source, title=f"{source.title} ({self._source_titles[source.title]})")
        self._stream_writer(source)

    def _write_text(self, text: str) -> None:
        self._text += text
        self._stream_writer(text)


class RespondNode:
    """Writes the reply to the stream while the model writes it, as a `StreamedReply`.

    Callable as a LangGraph node: `await node(state, runtime)`.
    """

    def __init__(self, config: RespondNodeConfig):
        self._config = config

    async def __call__(self, state: BotState, runtime: Runtime[Bot]) -> Command:
        bot = runtime.context
        announce(STATUS_RESPONDING, runtime)

        schema = self._config.response_schema
        reply = StreamedReply(schema, self._config.retrieved_sources(state["messages"]), runtime.stream_writer)
        compiler = self._config.compiler
        response = await stream_structured_response(
            bot.model_for(compiler.config.model_choice), compiler.compile(bot, state), schema, reply.grow
        )
        # A failed call's last block may be half-written, so only a complete response has it processed.
        if response is not None:
            reply.end(response)
        # A call cut off midway can't take back what is out, so the apology follows it.
        if response is None or not reply.text:
            await reply.write_paragraph(no_answer(bot.prompt_search_path, state.get("lang_code")))
        return Command(goto=END, update={"messages": [AIMessage(content=reply.text)]})


def make_respond_node(**config) -> RespondNode:
    """Returns a node that writes the reply to the stream while the model writes it.

    Keywords are `RespondNodeConfig` fields.
    """
    return RespondNode(RespondNodeConfig(**config))
