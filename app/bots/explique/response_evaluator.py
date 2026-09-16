import logging
from dataclasses import dataclass
from enum import StrEnum

from app.bots.explique.utils import casefold_and_collapse_whitespace

logger = logging.getLogger(__name__)


class EvaluationTag(StrEnum):
    NORMAL_RESPONSE = "normal_response"
    REPETITIVE = "repetitive"


class ResolutionAction(StrEnum):
    """What happens to a candidate response once the retry budget is spent."""

    DELIVER = "deliver"  # ship the last candidate anyway; a repeat beats no reply
    SUPPRESS = "suppress"  # drop the candidate instead of delivering it


@dataclass(frozen=True)
class EvaluatorContext:
    """Everything a response is checked against."""

    prior_turns: tuple[str, ...]


@dataclass(frozen=True)
class EvaluatorOutput:
    tags: tuple[EvaluationTag, ...]

    @property
    def is_clean(self) -> bool:
        return self.tags == (EvaluationTag.NORMAL_RESPONSE,)


class ResponseEvaluator:
    """Reviews the assistant's responses and decides whether to deliver them or retry."""

    RESOLUTIONS_MAP = {EvaluationTag.REPETITIVE: ResolutionAction.DELIVER}
    MAX_RETRIES = 1

    # Priority queue when there are more than one tag; most severe first.
    TAG_PRIORITY = (EvaluationTag.REPETITIVE,)

    @staticmethod
    def get_prioritized_tag(tags: tuple[EvaluationTag, ...]) -> EvaluationTag:
        for tag in ResponseEvaluator.TAG_PRIORITY:
            if tag in tags:
                return tag
        logger.warning("No priority set for %s; falling back to the first tag, which should not happen", tags)
        return tags[0]

    @staticmethod
    def get_resolution_action(tag: EvaluationTag) -> ResolutionAction:
        resolution = ResponseEvaluator.RESOLUTIONS_MAP.get(tag)
        if resolution is None:
            logger.warning("No resolution set for %s; falling back to delivering it", tag)
            return ResolutionAction.DELIVER
        return resolution

    @staticmethod
    def scan_repetitions(response: str, context: EvaluatorContext) -> EvaluationTag | None:
        """The assistant repeated itself verbatim."""
        response = casefold_and_collapse_whitespace(response)
        for prior in reversed(context.prior_turns):
            if response == casefold_and_collapse_whitespace(prior):
                return EvaluationTag.REPETITIVE
        return None

    DETERMINISTIC_METRICS = (scan_repetitions,)

    @staticmethod
    def deterministic_metrics(response: str, context: EvaluatorContext) -> tuple[EvaluationTag, ...]:
        tags = (metric(response, context) for metric in ResponseEvaluator.DETERMINISTIC_METRICS)
        return tuple(tag for tag in tags if tag is not None)

    @staticmethod
    def evaluate(response: str, context: EvaluatorContext) -> EvaluatorOutput:
        """Every finding against `response`; `NORMAL_RESPONSE` when there are none."""
        tags = ResponseEvaluator.deterministic_metrics(response, context)
        return EvaluatorOutput(tags=tags or (EvaluationTag.NORMAL_RESPONSE,))

    @staticmethod
    def may_reject(response_prefix: str, context: EvaluatorContext) -> bool:
        """Whether `response_prefix` could grow into a response `evaluate` rejects."""
        response_prefix = casefold_and_collapse_whitespace(response_prefix)
        return any(casefold_and_collapse_whitespace(prior).startswith(response_prefix) for prior in context.prior_turns)
