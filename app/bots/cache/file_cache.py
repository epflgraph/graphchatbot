import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from secrets import token_hex

from app.config import config

logger = logging.getLogger(__name__)

# Defaults to the OS temp dir, which is ephemeral; override via config for a persistent location.
# A specific cache (e.g. `image_transcriptions.py`) appends its own stem to this root.
DEFAULT_CACHE_ROOT = Path(tempfile.gettempdir()) / ".cache" / "chatbot"
CACHE_ROOT = config.cache.cache_dir or DEFAULT_CACHE_ROOT


@dataclass(frozen=True)
class CacheKey:
    """A cache key, used verbatim as a filename."""

    value: str


@dataclass(frozen=True)
class FileCache:
    """Text entries under one directory, one file per key; a miss or a failed write just logs and moves on, never raises."""

    root: Path

    def get(self, key: CacheKey) -> str | None:
        """The entry stored under `key`, or None on a miss; including a corrupted or unreadable one."""
        path = self._path_for(key)
        if not path.exists():
            return None

        try:
            entry = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            logger.warning("Cache entry unreadable, treating it as a miss: %s", path)
            return None

        logger.debug("Cache hit: %s", path)
        return entry

    def put(self, key: CacheKey, entry: str) -> None:
        """Store `entry` under `key`, creating the directory if it isn't there yet."""
        target = self._path_for(key)
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            # Write elsewhere and rename into place: `replace` is atomic, so a
            # reader sees the whole entry or none of it — across processes, no lock needed.
            scratch = target.with_name(f"{target.name}.{token_hex(64)}")
            scratch.write_text(entry, encoding="utf-8")
            scratch.replace(target)
        except OSError:
            logger.warning("Could not write cache entry: %s", target, exc_info=True)

    def _path_for(self, key: CacheKey) -> Path:
        return self.root / key.value
