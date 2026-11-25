import json
import logging

from langchain_core.messages import BaseMessage

from app.bots.callbacks.base import ToolRound, ToolRoundContext

logger = logging.getLogger(__name__)


def _dedupe_by_content(entries: list, seen: set[str]) -> list:
    """`entries` with repeats gone, keyed on each entry's content. The overlap
    several tool results share lands in here; the first occurrence of a content
    wins, which keeps each result's own ranking order intact."""
    unique = []
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("content"), str):
            if entry["content"] in seen:
                continue
            seen.add(entry["content"])
        unique.append(entry)
    return unique


def _dedupe_round_by_content(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Parallel tool calls overlap: keep the first occurrence of every entry
    across all of a round's tool results, keyed on content itself — chunks
    cut from the same document share its url yet differ in content, and
    remote indexes may also return the very same chunk twice."""
    seen = set()
    deduped = []
    for message in messages:
        if message.type != "tool":
            deduped.append(message)
            continue

        content = message.content
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                deduped.append(message)
                continue
        elif isinstance(content, list):
            parsed = content
        else:
            deduped.append(message)
            continue

        if not isinstance(parsed, list):
            deduped.append(message)
            continue

        filtered = _dedupe_by_content(parsed, seen)
        if len(filtered) < len(parsed):
            logger.info("Dropped %d duplicate entries.", len(parsed) - len(filtered))
            message = message.model_copy(update={"content": json.dumps(filtered)})
        deduped.append(message)
    return deduped


async def dedupe_tool_results(tool_round_context: ToolRoundContext, tool_round: ToolRound) -> None:
    """Drops the entries a round's tool results returned more than once."""
    tool_round.results[:] = _dedupe_round_by_content(tool_round.results)
