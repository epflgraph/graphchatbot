import logging

from langchain_core.messages import AIMessage
from langgraph.constants import TAG_NOSTREAM
from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import Command

from app.bots.base import Bot
from app.bots.explique.compilers.respond import compiler_for
from app.bots.explique.models import StudentIntent
from app.bots.explique.state import ExpliqueBotState
from app.compilation.invoke import text_call

logger = logging.getLogger(__name__)


def make_respond_node(on_candidate_response: str):
    """Generates the tutor's response and sends it to be checked before delivery."""

    async def respond_node(state: ExpliqueBotState, runtime: Runtime[Bot]) -> Command:
        """Looks up the reply by category, except a filled practice request,
        whose material comes from `practice` and skips generation entirely."""
        bot = runtime.context
        category = state.get("category")

        if category == StudentIntent.REQUEST_PRACTICE:
            practice_response = state.get("practice_response")
            if practice_response is not None:
                logger.info("Returning practice material")
                # Precomputed, so a retry would spend the budget for nothing.
                return Command(goto=END, update={"messages": [AIMessage(content=practice_response)]})

        logger.info("Responding to a %s turn", category)

        # TAG_NOSTREAM stops tokens streaming as they're produced; writing to
        # `candidate_response` instead of `messages` stops the finished message from
        # leaking too; both matter, since a rejected reply is regenerated here.
        response = await text_call(bot, compiler_for(category), state, tags=(TAG_NOSTREAM,))

        return Command(goto=on_candidate_response, update={"candidate_response": response})

    return respond_node
