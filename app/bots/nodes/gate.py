import logging

from pydantic import BaseModel

from langgraph.runtime import Runtime
from langgraph.types import Command

from app.bots.base import Bot
from app.llms import build_prompt_from_message_list, generate_structured_response

logger = logging.getLogger(__name__)


def make_gate_node(question: str, if_yes: str, if_no: str):
    """
    Returns a gate node that asks the LLM a yes/no question about the conversation
    and routes to if_yes or if_no accordingly.

    Args:
        question: yes/no question to ask about the conversation history.
        if_yes:   node to route to if the answer is yes.
        if_no:    node to route to if the answer is no (also used as fallback on LLM failure).
    """

    async def gate_node(state, runtime: Runtime[Bot]) -> Command:
        bot = runtime.context

        system_prompt = (
            "You will be given a conversation between a Human and an AI assistant.\n"
            f"Answer the following yes/no question about the conversation:\n{question}"
        )
        human_prompt = build_prompt_from_message_list(state['messages'])

        class Answer(BaseModel):
            answer: bool

        result = await generate_structured_response(bot.light_model, system_prompt, human_prompt, Answer)
        if result is None:
            logger.warning(f"Gate '{question[:40]}...' LLM call failed, defaulting to if_no='{if_no}'")
            return Command(goto=if_no)
        logger.info(f"Gate '{question[:40]}...' → {result.answer}")
        return Command(goto=if_yes if result.answer else if_no)

    return gate_node
