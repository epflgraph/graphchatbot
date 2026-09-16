from app.bots.cache.file_cache import CACHE_ROOT, FileCache

_ROOT = CACHE_ROOT / "topic-points"

# The points a topic is graded against, derived once and reused. Every student on
# a topic has to be held to the same standard, and the material is part of the key — so
# a course whose slides change derives a new standard instead of grading against the old.
CACHE = FileCache(_ROOT, "points")

# What each cached record was derived for: topic, index, whether material backed it,
# when. Entries live in directories named by a hash, so nothing else on disk
# identifies them — this is what lets one be inspected or deleted by hand.
PROVENANCE = FileCache(_ROOT, "provenance.json")
