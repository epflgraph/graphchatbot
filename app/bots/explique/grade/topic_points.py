import json
import logging
from datetime import datetime
from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.cache import topic_points as cache
from app.bots.cache.file_cache import CacheKey
from app.bots.cache.llm_call_cache_key import make_cache_key
from app.bots.explique.compilers.base import ExpliqueCompiler
from app.bots.explique.grade.compilers.topic_points import SourcedTopicPointsCompiler, UnsourcedTopicPointsCompiler
from app.bots.explique.grade.models import TopicPoints
from app.bots.explique.grade.topic_retrieval import fetch_topic_material
from app.bots.explique.grade.topics import Topic
from app.compilation.invoke import structured_call
from app.logging_config import truncate

logger = logging.getLogger(__name__)


def _cache_key(bot: Bot, compiler: type[ExpliqueCompiler], call_state: Mapping[str, Any]) -> CacheKey:
    """SHA-256 of the whole call that produced the points: prompt, material, and model.

    Not the inputs alone — a topic would then keep a standard derived under rules or a
    model that no longer exist, with nothing to signal it.
    """
    model = bot.model_for(compiler.config.model_choice)
    return make_cache_key(
        messages=compiler.compile(bot, call_state),
        bot_name=bot.name,
        model_settings={
            "model_name": model.model_name,
            "temperature": model.temperature,
            "top_p": model.top_p,
            "presence_penalty": model.presence_penalty,
            "extra_body": model.extra_body,
        },
    )


def _provenance(bot: Bot, topic: Topic, *, sourced: bool) -> str:
    """The provenance of a cache record: what it was derived for, and from what."""
    return json.dumps(
        {
            "index": bot.index,
            "topic": topic.name,
            "sourced": sourced,
            "derived_at": datetime.now().isoformat(timespec="seconds"),
        },
        ensure_ascii=False,
    )


async def derive_topic_points(bot: Bot, topic: Topic, state: Mapping[str, Any]) -> tuple[str, ...]:
    """The points `topic` has to cover, derived once and cached: the standard is shared across
    students so two equal explanations grade the same. From the course material when the
    index has any, otherwise from the topic name alone."""
    material = await fetch_topic_material(bot.index, topic.name)
    if not material:
        logger.warning("No material for topic %r in index %r; deriving points unsourced", topic.name, bot.index)

    compiler = SourcedTopicPointsCompiler if material else UnsourcedTopicPointsCompiler

    call_state = {**state, "topic_material": material}

    key = _cache_key(bot, compiler, call_state)
    if (cached := cache.CACHE.get(key)) is not None:
        return tuple(json.loads(cached))

    derived = await structured_call(bot=bot, compiler=compiler, state=call_state, fallback=TopicPoints())
    if not derived.points:
        logger.warning("No points derived for topic %r in index %r; the exercise cannot finish", topic.name, bot.index)
        return ()

    cache.CACHE.put(key, json.dumps(derived.points, ensure_ascii=False))
    cache.PROVENANCE.put(key, _provenance(bot, topic, sourced=bool(material)))
    logger.info("Derived points for topic %r (%s): %s", topic.name, truncate(derived.reasoning), derived.points)
    return tuple(derived.points)
