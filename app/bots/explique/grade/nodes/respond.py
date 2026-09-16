import logging

from langgraph.constants import TAG_NOSTREAM
from langgraph.runtime import Runtime
from langgraph.types import Command

from app.bots.base import Bot
from app.bots.explique.grade.compilers.respond import compiler_for
from app.bots.explique.grade.state import GradeBotState
from app.bots.explique.grade.stream_gate import StreamGate
from app.bots.explique.response_evaluator import EvaluatorContext
from app.bots.transcript import all_assistant_turns
from app.compilation.invoke import text_call

logger = logging.getLogger(__name__)


def make_respond_node(on_candidate_response: str):
    """Generates the candidate response, streaming whatever the evaluator can no longer reject."""

    async def respond_node(state: GradeBotState, runtime: Runtime[Bot]) -> Command:
        bot = runtime.context
        category = state.get("category")
        logger.info("Responding to a %s turn", category)

        compiler = compiler_for(category)
        dialog = compiler.apply_callbacks(state)["messages"]
        context = EvaluatorContext(prior_turns=all_assistant_turns(dialog))

        gate = StreamGate(context, runtime.stream_writer)
        response = await text_call(bot, compiler, state, tags=(TAG_NOSTREAM,), stream_writer=gate.feed)

        return Command(
            goto=on_candidate_response,
            update={"candidate_response": response, "not_streamed_response": response.removeprefix(gate.streamed)},
        )

    return respond_node
