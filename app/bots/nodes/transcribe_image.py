import asyncio
import logging
from dataclasses import dataclass, field
from functools import partial
from typing import ClassVar

from langchain_core.messages import BaseMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from app.bots.base import Bot, BotState, StateUpdate
from app.bots.cache import image_transcriptions
from app.bots.cache.file_cache import CacheKey
from app.bots.cache.llm_call_cache_key import make_cache_key
from app.compilation.base import MessageCompiler
from app.llms.utils import generate_structured_response, has_image_part

logger = logging.getLogger(__name__)


# Placeholder text for unreadable image.
UNREADABLE_IMAGE_TEXT = "<user uploaded image>"


class ImageTranscription(BaseModel):
    """What an image a user sent says, rendered as if they had typed it."""

    readable: bool = Field(description="Whether the image carries anything to transcribe.")
    transcription: str = Field(
        default=UNREADABLE_IMAGE_TEXT,
        description="The image's content, transcribed as the user's own turn and written in their voice.",
    )

    @model_validator(mode="after")
    def _drop_transcription_if_unreadable(self) -> Self:
        """If an image carries nothing to transcribe, set its transcription to the placeholder text."""
        if not self.readable:
            self.transcription = UNREADABLE_IMAGE_TEXT
        return self


@dataclass(frozen=True)
class ImageTranscriber:
    """Transcribes one image turn to text for `bot`, reading
    from the cache when necessary and feasible."""

    # The transcription attempts one image gets before it is left unread. Only the
    # first runs with the model's full budget: a miss can also mean a cleared cache
    # under a resumed conversation, not just an earlier failure.
    MAX_TRANSCRIPTION_ATTEMPTS: ClassVar[int] = 3
    RETRY_TIMEOUT_SECONDS: ClassVar[float] = 15.0
    MAX_CONCURRENT_TRANSCRIPTIONS: ClassVar[int] = 16

    bot: Bot
    compiler: type[MessageCompiler]
    call_slots: asyncio.Semaphore = field(default_factory=partial(asyncio.Semaphore, MAX_CONCURRENT_TRANSCRIPTIONS))

    def _cache_key(self, compiled: list[BaseMessage]) -> CacheKey:
        """The cache key for a call: `compiled`, the bot, and the model settings that affect its output."""
        model = self.bot.model_for(self.compiler.config.model_choice)
        return make_cache_key(
            messages=compiled,
            bot_name=self.bot.name,
            model_settings={
                "model_name": model.model_name,
                "temperature": model.temperature,
                "top_p": model.top_p,
                "presence_penalty": model.presence_penalty,
                "extra_body": model.extra_body,
            },
        )

    @staticmethod
    def _get_attempts(cache_key: CacheKey) -> int:
        """How many times the transcription of an image has failed.

        A count that isn't there — a new image, or a cache cleared under a resumed
        conversation — or one that isn't readable is none, so the image is read
        again rather than ignored.
        """
        attempts = image_transcriptions.ATTEMPTS.get(cache_key)
        if attempts is not None:
            try:
                return int(attempts)
            except ValueError:
                logger.warning("Attempt count is not a number (%r); reading the image again", attempts)
        return 0

    async def run(self, message: BaseMessage) -> BaseMessage:
        """`message` with its image transcribed, checking the cache first."""
        compiled_messages = self.compiler.compile(self.bot, {"messages": [message]})
        cache_key = self._cache_key(compiled_messages)
        transcription = image_transcriptions.CACHE.get(cache_key)

        if transcription is None:
            # Cache miss
            result = await self._read_image(cache_key, compiled_messages)
            transcription = UNREADABLE_IMAGE_TEXT if result is None else result.transcription

            # Never cache a failure; only the attempt that produced it. An image that carries
            # nothing is an answer, not a failure, so later turns don't read it again.
            if result is not None:
                image_transcriptions.CACHE.put(cache_key, transcription)

        return message.model_copy(update={"content": transcription})

    async def _read_image(self, cache_key: CacheKey, compiled: list[BaseMessage]) -> BaseModel | None:
        """Read an image the cache holds no transcription for, recording a failed attempt.

        Retries are bounded because the client resends the whole conversation: an
        image nobody can read would otherwise cost a call on every remaining turn.
        """
        attempts = self._get_attempts(cache_key)
        if attempts >= self.MAX_TRANSCRIPTION_ATTEMPTS:
            logger.debug("Leaving image unread after %s failed attempts", attempts)
            return None

        async with self.call_slots:
            call = generate_structured_response(
                model=self.bot.model_for(self.compiler.config.model_choice),
                messages=compiled,
                output_schema=self.compiler.config.output_schema,
            )
            if attempts:
                call = asyncio.wait_for(call, timeout=self.RETRY_TIMEOUT_SECONDS)

            try:
                result = await call
            except asyncio.TimeoutError:
                logger.warning("Gave up re-reading an image after %ss", self.RETRY_TIMEOUT_SECONDS)
                result = None

        if result is None:
            image_transcriptions.ATTEMPTS.put(cache_key, str(attempts + 1))
        return result


def make_image_transcriber_node(compiler: type[MessageCompiler], on_unreadable: str):
    """Returns a node that transcribes every image in the conversation.

    `on_unreadable` is a `category`, not a node name; `compiler`'s schema must
    carry a `transcription` field that reads `UNREADABLE_IMAGE_TEXT` when nothing was
    read, as `ImageTranscription` does. `compiler` is given each image turn alone.
    """

    async def image_transcriber_node(state: BotState, runtime: Runtime[Bot]) -> StateUpdate:
        """Transcribe every image in the conversation to text."""

        messages = state["messages"]

        image_turns = [message for message in messages if message.type == "human" and has_image_part(message.content)]
        if not image_turns:
            return {}

        transcriber = ImageTranscriber(runtime.context, compiler)
        async_tasks = (transcriber.run(turn) for turn in image_turns)
        results = await asyncio.gather(*async_tasks)

        # Update only the messages that got transcribed here, not the whole dialog.
        # This happens by id: each result keeps its original turn's id, so `add_messages`
        # replaces it in place instead of appending a duplicate.
        state_update = {"messages": list(results)}

        latest_message = messages[-1]
        latest_message_has_image = has_image_part(latest_message.content)
        latest_transcription = results[-1]

        if latest_message_has_image and latest_transcription.content == UNREADABLE_IMAGE_TEXT:
            state_update["category"] = on_unreadable

        return state_update

    return image_transcriber_node
