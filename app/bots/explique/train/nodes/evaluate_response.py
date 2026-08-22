import logging

from langchain_core.messages import AIMessage
from langgraph.graph import END
from langgraph.types import Command

from app.bots.explique.train.models import RejectedResponse
from app.bots.explique.train.response_evaluator import EvaluatorContext, ResolutionAction, ResponseEvaluator
from app.bots.explique.train.state import ExpliqueBotState
from app.bots.explique.train.transcript import all_assistant_turns
from app.compilation.base import MessageCompiler
from app.logging_config import truncate

logger = logging.getLogger(__name__)


def _deliver(candidate_response: str) -> Command:
    """Delivers `candidate_response` as a fresh `AIMessage` — LangGraph won't emit one whose id it's already seen."""
    return Command(goto=END, update={"messages": [AIMessage(content=candidate_response)]})


def make_evaluate_response_node(on_retry: str, compiler: type[MessageCompiler]):
    """Checks this turn's candidate response and either delivers it or sends it back to `on_retry`.

    Reads the conversation through `compiler`, so the evaluator judges repetition
    against the same turns the responder was given.
    """

    async def evaluate_response_node(state: ExpliqueBotState) -> Command:
        candidate_response = state["candidate_response"]
        rejected_responses = state.get("rejected_responses", ())

        dialog = compiler.apply_callbacks(state)["messages"]
        context = EvaluatorContext(prior_turns=all_assistant_turns(dialog))
        evaluation = ResponseEvaluator.evaluate(candidate_response, context)

        if evaluation.is_clean:
            return _deliver(candidate_response)

        tag = ResponseEvaluator.get_prioritized_tag(evaluation.tags)
        retries_made = len(rejected_responses)

        if retries_made < ResponseEvaluator.MAX_RETRIES:
            logger.warning(
                "Rejected candidate response as %s on retry %d of %d, regenerating: %s",
                tag,
                retries_made + 1,
                ResponseEvaluator.MAX_RETRIES,
                truncate(candidate_response),
            )
            return Command(
                goto=on_retry,
                update={
                    "rejected_responses": (*rejected_responses, RejectedResponse(response=candidate_response, tag=tag))
                },
            )

        resolution = ResponseEvaluator.get_resolution_action(tag)
        if resolution is not ResolutionAction.DELIVER:
            # TODO: handle non-DELIVER resolutions (e.g. SUPPRESS) once one exists.
            raise NotImplementedError(f"No handling for resolution {resolution!s} of tag {tag!s}.")

        logger.warning("Exhausted all %d retry(ies), delivering the last candidate anyway", retries_made)
        return _deliver(candidate_response)

    return evaluate_response_node
