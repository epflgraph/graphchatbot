import logging
from typing import Callable, Literal

from langgraph.runtime import Runtime
from pydantic import BaseModel

from app.bots.base import Bot
from app.llms import build_prompt_from_message_list, generate_structured_response

logger = logging.getLogger(__name__)


def make_classify_node(categories: dict[str, dict] | Callable):
    """
    Returns a classify node that classifies the conversation into one of the given categories.

    Args:
        categories: dict mapping category name to a dict with keys:
                    - 'description': str describing the category
                    - 'tool_choice': Optional[str], passed to bind_tools (None, 'any', or a tool name)
                    e.g. {'greeting': {'description': 'The user is greeting...', 'tool_choice': None}}

                    May also be a callable that receives the current state and returns such a dict,
                    for cases where eligible categories depend on runtime state (e.g. message count).
    """

    async def classify_node(state, runtime: Runtime[Bot]) -> dict:
        bot = runtime.context

        categories_dict = categories(state) if callable(categories) else categories

        categories_prompt = "\n".join([f"* {name}: {cat['description']}" for name, cat in categories_dict.items()])
        system_prompt = f"""You will be given a conversation between a Human and an AI system.
Your task is to classify the conversation based on the last request.
The possible categories are the following:
{categories_prompt}"""

        human_prompt = build_prompt_from_message_list(state["messages"])

        class Category(BaseModel):
            category: Literal[*list(categories_dict.keys())]

        result = await generate_structured_response(bot.light_model, system_prompt, human_prompt, Category)
        if result is None:
            category = list(categories_dict.keys())[0]
            logger.warning(f"Classify LLM call failed, defaulting to '{category}'")
        else:
            category = result.category
        logger.info(f"Classified as `{category}`")

        return {
            "category": category,
            "tool_choice": categories_dict[category].get("tool_choice"),
        }

    return classify_node
