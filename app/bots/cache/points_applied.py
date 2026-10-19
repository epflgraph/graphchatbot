from app.bots.cache.file_cache import CACHE_ROOT, FileCache

# The points applied on each graded turn, so a point once applied is never taken back.
CACHE = FileCache(CACHE_ROOT / "points-applied", "points")
