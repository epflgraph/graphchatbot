import functools
from collections.abc import Callable

from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.grade.prompts import STATUS_TRANSCRIBING_TEMPLATE
from app.bots.explique.grade.state import GradeBotState
from app.bots.utils import announce
from app.llms.utils import has_image_part


def make_transcribe_image_node(transcriber_node: Callable):
    """The shared transcription node, with a status line written when the turn carries a photo."""
    return functools.partial(_transcribe_image_node, transcriber_node)


async def _transcribe_image_node(transcriber_node, state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    # Earlier photos come back from the cache; announcement happens only for the latest turn.
    if has_image_part(state["messages"][-1].content):
        announce(STATUS_TRANSCRIBING_TEMPLATE, runtime)
    return await transcriber_node(state, runtime)
