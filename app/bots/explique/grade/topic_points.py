import json
import logging
from datetime import datetime
from typing import Any, Mapping

from pydantic import TypeAdapter, ValidationError

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

_TOPIC_POINTS_SCHEMA = TypeAdapter(list[str])


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
    students so two equal explanations grade the same. Points are derived from the course material
    when it teaches the topic, otherwise from the topic name alone."""
    material = await fetch_topic_material(bot.index, topic.name)
    points = await _derive_topic_points(bot, topic, state, material) if material else ()
    if points:
        # Sourced points are the preferred standard while unsourced ones are a fallback.
        # Given that at least one retrieval has succeeded, if a later one fails, we'll still
        # grade on the cached sourced points.
        _cache_as_unsourced(bot, topic, state, points)
        return points

    logger.info("No material teaching topic %r in index %r; deriving points unsourced", topic.name, bot.index)
    return await _derive_topic_points(bot, topic, state, material="")


def _cache_as_unsourced(bot: Bot, topic: Topic, state: Mapping[str, Any], points: tuple[str, ...]) -> None:
    """Cache sourced points under the unsourced key."""
    key = _cache_key(bot, UnsourcedTopicPointsCompiler, {**state, "topic_material": ""})
    entry = json.dumps(list(points), ensure_ascii=False)
    if cache.CACHE.get(key) != entry:
        cache.CACHE.put(key, entry)
        cache.PROVENANCE.put(key, _provenance(bot, topic, sourced=True))


async def _derive_topic_points(bot: Bot, topic: Topic, state: Mapping[str, Any], material: str) -> tuple[str, ...]:
    """One derivation, sourced when there is material, read from the cache when it ran before.
    An empty verdict on material is cached too, since the material is in its key."""
    compiler = SourcedTopicPointsCompiler if material else UnsourcedTopicPointsCompiler

    call_state = {**state, "topic_material": material}

    key = _cache_key(bot, compiler, call_state)
    if (cached := cache.CACHE.get(key)) is not None:
        try:
            return tuple(_TOPIC_POINTS_SCHEMA.validate_json(cached))
        except ValidationError:
            logger.warning(
                "Cached points for topic %r at %s are not a list of strings; deriving them again", topic.name, key.value
            )

    fallback = TopicPoints()
    derived = await structured_call(bot=bot, compiler=compiler, state=call_state, fallback=fallback)
    log_level = logging.INFO if derived.points else logging.WARNING
    logger.log(
        log_level, "Derived points for topic %r (%s): %s", topic.name, truncate(derived.reasoning), derived.points
    )

    if derived is not fallback and (derived.points or material):
        cache.CACHE.put(key, json.dumps(derived.points, ensure_ascii=False))
        cache.PROVENANCE.put(key, _provenance(bot, topic, sourced=bool(material)))
    return tuple(derived.points)
