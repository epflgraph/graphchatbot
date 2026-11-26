from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.bots.artifacts.rich_response import ResponseBlock, VideoBlock


class EvaluationTag(StrEnum):
    """What can be wrong with a response block."""

    UNGROUNDED = "ungrounded"


@dataclass(frozen=True)
class EvaluationContext:
    """Everything a response block is checked against."""

    urls: frozenset[str]  # every url a reply may cite from this turn's tool results


EvaluationMetric = Callable[["ResponseBlock", EvaluationContext], EvaluationTag | None]


def scan_urls(block: "VideoBlock", context: EvaluationContext) -> EvaluationTag | None:
    """Tag the block ungrounded if its url is hallucinated or wasn't retrieved this turn."""
    return None if block.url in context.urls else EvaluationTag.UNGROUNDED


def evaluate(block: "ResponseBlock", context: EvaluationContext) -> tuple[EvaluationTag, ...]:
    """Every finding against `block`; empty when there are none."""
    tags = (metric(block, context) for metric in block.EVALUATION_METRICS)
    return tuple(tag for tag in tags if tag is not None)
