import hashlib
import json
from typing import Any

from langchain_core.messages import BaseMessage

from app.bots.cache.file_cache import CacheKey


def make_cache_key(*, messages: list[BaseMessage], bot_name: str, model_settings: dict[str, Any]) -> CacheKey:
    """SHA-256 hash of the canonical JSON of the compiled call, the bot, and the model's settings."""
    call = [[message.type, message.content] for message in messages]  # not `id`, which varies per turn
    dump = json.dumps([call, bot_name, model_settings], sort_keys=True, ensure_ascii=True)
    return CacheKey(hashlib.sha256(dump.encode("utf-8")).hexdigest())
