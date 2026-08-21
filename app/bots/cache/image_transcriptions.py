from app.bots.cache.file_cache import CACHE_ROOT, FileCache

_ROOT = CACHE_ROOT / "image-transcriptions"

CACHE = FileCache(_ROOT, "transcription")

# Failed attempts, not failed transcriptions: nothing stored here is served to a prompt.
# Counting them is what stops an unreadable image being read again on every later turn.
ATTEMPTS = FileCache(_ROOT, "attempts")
