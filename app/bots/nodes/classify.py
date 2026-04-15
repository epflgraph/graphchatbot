from typing import Literal

from pydantic import BaseModel

from langgraph.runtime import Runtime

from app.bots.base import Bot
from app.llms import build_prompt_from_message_list, generate_structured_response


def make_classify_node(categories: dict[str, str]):
    """
    Returns a classify node that classifies the conversation into one of the given categories.

    Args:
        categories: dict mapping category name to its description, e.g.
                    {'greeting': 'The user is greeting...', 'main': '...'}
    """

    async def classify_node(state, runtime: Runtime[Bot]) -> dict:
        bot = runtime.context

        categories_prompt = '\n'.join([f'* {name}: {desc}' for name, desc in categories.items()])
        system_prompt = f"""You will be given a conversation between a Human and an AI system.
Your task is to classify the conversation based on the last request.
The possible categories are the following:
{categories_prompt}"""

        human_prompt = build_prompt_from_message_list(state['messages'])

        class Category(BaseModel):
            category: Literal[*list(categories.keys())]

        result = await generate_structured_response(bot.light_model, system_prompt, human_prompt, Category)
        print('[CLASSIFY]', f"Classified as `{result.category}`")

        return {'category': result.category}

    return classify_node
