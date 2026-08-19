import logging
from dataclasses import dataclass
from enum import StrEnum

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
    def _normalize(text: str) -> str:
        """Casefolded, with runs of whitespace collapsed, so a repeat differing
        only in spacing or capitalization still counts as one."""
        return " ".join(text.split()).casefold()

    @staticmethod
    def scan_repetitions(response: str, context: EvaluatorContext) -> EvaluationTag | None:
        """The assistant repeated itself verbatim."""
        response = ResponseEvaluator._normalize(response)
        for prior in reversed(context.prior_turns):
            if response == ResponseEvaluator._normalize(prior):
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
