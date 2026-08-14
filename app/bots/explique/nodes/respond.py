import logging

from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.compilers import COMPILERS
from app.bots.explique.compilers.base import ExpliqueTask
from app.bots.explique.models import StudentIntent
from app.bots.explique.state import ExpliqueBotState

logger = logging.getLogger(__name__)


async def respond_node(state: ExpliqueBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Generate the tutor's response: a registry lookup by category (`compilers/respond.py`),
    except `request-practice`, whose material comes from the `practice` node and is returned
    verbatim, falling through to the compiler only if that node produced nothing."""
    bot = runtime.context
    category = state.get("category")

    if category == StudentIntent.REQUEST_PRACTICE:
        practice_response = state.get("practice_response")
        if practice_response is not None:
            logger.info("Returning practice material")
            return {"messages": [AIMessage(content=practice_response)]}

    logger.info("Responding to a %s turn", category)

    compiler = COMPILERS.get(ExpliqueTask.RESPOND, category)
    response = await bot.model_for(compiler.config.model_choice).ainvoke(compiler.compile(bot, state))

    return {"messages": [response]}
