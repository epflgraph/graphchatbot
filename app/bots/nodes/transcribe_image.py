import asyncio
import logging
from dataclasses import dataclass
from typing import ClassVar

from langchain_core.messages import BaseMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from app.bots.base import Bot, BotState, StateUpdate
from app.bots.cache import image_transcriptions
from app.bots.cache.file_cache import CacheKey
from app.bots.cache.llm_call_cache_key import make_cache_key
from app.compilation.base import MessageCompiler
from app.llms.utils import generate_structured_response, has_image_part

logger = logging.getLogger(__name__)


class ImageTranscription(BaseModel):
    """What an image a user sent says, rendered as if they had typed it."""

    transcription: str = Field(
        default="<user uploaded image>",
        description="The image's content, transcribed as the user's own turn and written in their voice.",
    )


@dataclass(frozen=True)
class TranscriptionResult:
    """One image turn rewritten to text, and whether
    the transcription was successful or fell back to the default."""

    failed: bool
    message: BaseMessage


@dataclass(frozen=True)
class ImageTranscriber:
    """Transcribes one image turn to text for `bot`, reading
    from the cache when necessary and feasible."""

    # The transcription attempts one image gets before it is left unread. Only the
    # first runs with the model's full budget: a miss can also mean a cleared cache
    # under a resumed conversation, not just an earlier failure.
    MAX_TRANSCRIPTION_ATTEMPTS: ClassVar[int] = 3
    RETRY_TIMEOUT_SECONDS: ClassVar[float] = 15.0

    bot: Bot
    compiler: type[MessageCompiler]

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

    async def run(self, messages: list[BaseMessage]) -> TranscriptionResult:
        """Transcribe the image in the last turn of `messages`, checking the cache first."""
        compiled_messages = self.compiler.compile(self.bot, {"messages": messages})
        cache_key = self._cache_key(compiled_messages)
        cached_transcription = image_transcriptions.CACHE.get(cache_key)

        if cached_transcription is not None:
            # Cache hit
            failed = False
            rewritten = messages[-1].model_copy(update={"content": cached_transcription})
        else:
            # Cache miss
            result = await self._read_image(cache_key, compiled_messages)
            failed = result is None
            transcription = ImageTranscription().transcription if failed else result.transcription

            # Never cache a failure — only the attempt that produced it
            if not failed:
                image_transcriptions.CACHE.put(cache_key, transcription)

            rewritten = messages[-1].model_copy(update={"content": transcription})

        return TranscriptionResult(message=rewritten, failed=failed)

    async def _read_image(self, cache_key: CacheKey, compiled: list[BaseMessage]) -> BaseModel | None:
        """Read an image the cache holds no transcription for, recording a failed attempt.

        Retries are bounded because the client resends the whole conversation: an
        image nobody can read would otherwise cost a call on every remaining turn.
        """
        attempts = self._get_attempts(cache_key)
        if attempts >= self.MAX_TRANSCRIPTION_ATTEMPTS:
            logger.debug("Leaving image unread after %s failed attempts", attempts)
            return None

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
    carry a `transcription` field, as `ImageTranscription` does.
    """

    async def image_transcriber_node(state: BotState, runtime: Runtime[Bot]) -> StateUpdate:
        """Transcribe every image in the conversation to text."""

        messages = state["messages"]

        # Each context is the transcript up to and including one image turn — that
        # prefix becomes that image's own dialog history, so transcription can resolve
        # notation from what preceded it without leaking what came after.
        image_contexts = [
            messages[: idx + 1]
            for idx, message in enumerate(messages)
            if message.type == "human" and has_image_part(message.content)
        ]
        if not image_contexts:
            return {}

        transcriber = ImageTranscriber(runtime.context, compiler)
        async_tasks = (transcriber.run(context) for context in image_contexts)
        results = await asyncio.gather(*async_tasks)

        # Update only the messages that got transcribed here, not the whole dialog.
        # This happens by id: each result keeps its original turn's id, so `add_messages`
        # replaces it in place instead of appending a duplicate.
        state_update = {"messages": [result.message for result in results]}

        latest_message = messages[-1]
        latest_message_has_image = has_image_part(latest_message.content)
        latest_transcription = results[-1]

        if latest_message_has_image and latest_transcription.failed:
            state_update["category"] = on_unreadable

        return state_update

    return image_transcriber_node
