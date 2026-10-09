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
from app.bots.explique.grade.compilers.topic_points import (
    GradeSourcedTopicPointsCompiler,
    GradeUnsourcedTopicPointsCompiler,
)
from app.bots.explique.grade.models import PointsProvenance, TopicPoints
from app.bots.explique.grade.topic_retrieval import fetch_topic_material
from app.bots.explique.grade.topics import Topic
from app.compilation.invoke import structured_call
from app.logging_config import truncate

logger = logging.getLogger(__name__)

_TOPIC_POINTS_SCHEMA = TypeAdapter(list[str])

# Max number of attempts to derive points from the course material,
# on a bot that doesn't allow unsourced points.
MAX_SOURCED_ATTEMPTS = 2


class TopicPointsUnavailable(Exception):
    """No points to grade the topic against."""


async def derive_topic_points(bot: Bot, topic: Topic, state: Mapping[str, Any]) -> tuple[str, ...]:
    """The points `topic` is graded against: from its material, else from its name if the bot allows it."""
    max_sourced_attempts = 1 if bot.allow_unsourced_points else MAX_SOURCED_ATTEMPTS
    if points := await _derive_sourced_points(bot, topic, state, max_sourced_attempts):
        return points

    if bot.allow_unsourced_points and (points := await _derive_unsourced_points(bot, topic, state)):
        return points

    raise TopicPointsUnavailable(topic.name)


async def _derive_sourced_points(
    bot: Bot, topic: Topic, state: Mapping[str, Any], max_attempts: int
) -> tuple[str, ...]:
    """Points from fresh material, tried up to `max_attempts` times, else the ones cached earlier."""
    for attempt in range(1, max_attempts + 1):
        material = await fetch_topic_material(bot.index, topic.name)
        points = await _derive_points_once(bot, topic, state, material) if material else None
        if points:
            _cache_sourced_as_unsourced(bot, topic, state, points)
            return points
        if points == ():
            logger.warning("The material in index %r doesn't teach topic %r", bot.index, topic.name)
            return ()
        if attempt < max_attempts:
            logger.warning(
                "No sourced points for topic %r in index %r on attempt %s of %s; trying again",
                topic.name,
                bot.index,
                attempt,
                max_attempts,
            )

    if cached := _cached_sourced_as_unsourced(bot, topic, state):
        logger.warning(
            "No fresh points for topic %r in index %r; grading on the sourced ones cached earlier",
            topic.name,
            bot.index,
        )
    return cached or ()


async def _derive_unsourced_points(bot: Bot, topic: Topic, state: Mapping[str, Any]) -> tuple[str, ...]:
    """Points from the topic name alone."""
    logger.info("Deriving points for topic %r in index %r from its name alone", topic.name, bot.index)
    return await _derive_points_once(bot, topic, state, material="") or ()


async def _derive_points_once(
    bot: Bot, topic: Topic, state: Mapping[str, Any], material: str
) -> tuple[str, ...] | None:
    """One derivation, sourced when there is material, read from the cache when it ran before.
    An empty verdict on material is cached too, since the material is in its key. None when the call failed."""
    compiler = GradeSourcedTopicPointsCompiler if material else GradeUnsourcedTopicPointsCompiler

    call_state = {**state, "topic_material": material}

    key = _cache_key(bot, compiler, call_state)
    if (cached := _cached_points(topic, key)) is not None:
        return cached

    fallback = TopicPoints()
    derived = await structured_call(bot=bot, compiler=compiler, state=call_state, fallback=fallback)
    if derived is fallback:
        return None

    log_level = logging.INFO if derived.points else logging.WARNING
    logger.log(
        log_level, "Derived points for topic %r (%s): %s", topic.name, truncate(derived.reasoning), derived.points
    )
    points = tuple(derived.points)
    if points or material:
        _cache_points(bot, topic, key, points, sourced=bool(material))
    return points


def _cache_sourced_as_unsourced(bot: Bot, topic: Topic, state: Mapping[str, Any], points: tuple[str, ...]) -> None:
    """Cache sourced points under the unsourced key, as the fallback for a later turn that derives none."""
    if _cached_sourced_as_unsourced(bot, topic, state) != points:
        _cache_points(bot, topic, _unsourced_cache_key(bot, state), points, sourced=True)


def _cached_sourced_as_unsourced(bot: Bot, topic: Topic, state: Mapping[str, Any]) -> tuple[str, ...] | None:
    """The points `_cache_sourced_as_unsourced` cached, or None when the unsourced key holds unsourced ones."""
    key = _unsourced_cache_key(bot, state)
    provenance = _cached_provenance(topic, key)
    return _cached_points(topic, key) if provenance and provenance.sourced else None


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


def _unsourced_cache_key(bot: Bot, state: Mapping[str, Any]) -> CacheKey:
    """Where unsourced points are cached, and where `_cache_sourced_as_unsourced` caches sourced ones."""
    return _cache_key(bot, GradeUnsourcedTopicPointsCompiler, {**state, "topic_material": ""})


def _cache_points(bot: Bot, topic: Topic, key: CacheKey, points: tuple[str, ...], *, sourced: bool) -> None:
    """Cache `points` under `key`, with their provenance: what they were derived for, and from what."""
    cache.CACHE.put(key, json.dumps(list(points), ensure_ascii=False))
    provenance = PointsProvenance(
        index=bot.index, topic=topic.name, sourced=sourced, derived_at=datetime.now().replace(microsecond=0)
    )
    cache.PROVENANCE.put(key, provenance.model_dump_json())


def _cached_points(topic: Topic, key: CacheKey) -> tuple[str, ...] | None:
    """The points cached under `key`, or None on a miss or an unreadable entry."""
    if (cached := cache.CACHE.get(key)) is None:
        return None
    try:
        return tuple(_TOPIC_POINTS_SCHEMA.validate_json(cached))
    except ValidationError:
        logger.warning(
            "Cached points for topic %r at %s are not a list of strings; ignoring them", topic.name, key.value
        )
        return None


def _cached_provenance(topic: Topic, key: CacheKey) -> PointsProvenance | None:
    """The provenance cached under `key`, or None on a miss or an unreadable entry."""
    if (cached := cache.PROVENANCE.get(key)) is None:
        return None
    try:
        return PointsProvenance.model_validate_json(cached)
    except ValidationError:
        logger.warning("Cached provenance for topic %r at %s is unreadable; ignoring it", topic.name, key.value)
        return None
