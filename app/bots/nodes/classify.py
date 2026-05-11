import logging
from typing import Literal

from pydantic import BaseModel

from langgraph.runtime import Runtime

from app.bots.base import Bot
from app.llms import build_prompt_from_message_list, generate_structured_response

logger = logging.getLogger(__name__)


def make_classify_node(categories: dict[str, dict]):
    """
    Returns a classify node that classifies the conversation into one of the given categories.

    Args:
        categories: dict mapping category name to a dict with keys:
                    - 'description': str describing the category
                    - 'force_tools': bool, whether to force tool use for this category
                    e.g. {'greeting': {'description': 'The user is greeting...', 'force_tools': False}}
    """

    async def classify_node(state, runtime: Runtime[Bot]) -> dict:
        bot = runtime.context

        categories_prompt = '\n'.join([f'* {name}: {cat["description"]}' for name, cat in categories.items()])
        system_prompt = f"""You will be given a conversation between a Human and an AI system.
Your task is to classify the conversation based on the last request.
The possible categories are the following:
{categories_prompt}"""

        human_prompt = build_prompt_from_message_list(state['messages'])

        class Category(BaseModel):
            category: Literal[*list(categories.keys())]

        result = await generate_structured_response(bot.light_model, system_prompt, human_prompt, Category)
        logger.info(f"Classified as `{result.category}`")

        return {
            'category': result.category,
            'force_tools': categories[result.category]['force_tools'],
        }

    return classify_node
