import logging

from app.interfaces.graphai import graphai

logger = logging.getLogger(__name__)

# A guess at how much material a topic needs.
MATERIAL_LIMIT = 30


async def fetch_topic_material(index: str, topic_name: str) -> str:
    """The course material `index` holds for `topic_name`, as one block of text."""
    result = await graphai.rag_retrieve(index=index, texts=[topic_name], limit=MATERIAL_LIMIT)

    if len(result.chunks) == MATERIAL_LIMIT:
        logger.debug(
            "Topic %r filled the %s-fragment limit in index %r; its points come from the most "
            "relevant fragments, not from everything the topic has",
            topic_name,
            MATERIAL_LIMIT,
            index,
        )

    contents = (chunk.content or chunk.content_en or chunk.content_fr for chunk in result.chunks)
    # Sorted, not left in retrieval order: this text is part of the points' cache key,
    # so a re-ranking would derive a second standard for the same topic.
    fragments = sorted({content for content in contents if content})
    logger.info("Retrieved %s fragment(s) for topic %r from index %r", len(fragments), topic_name, index)
    return "\n\n".join(fragments)
