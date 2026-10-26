from app.bots.callbacks.base import UNFORCED_TOOL_CHOICES, CallbackContext, LLMRequest
from app.bots.utils import STATUS_FETCHING, STATUS_RESPONDING, announce


async def announce_status(callback_context: CallbackContext, llm_request: LLMRequest) -> None:
    """Puts a line on screen saying whether the model is about to fetch or to respond."""
    is_forced = bool(llm_request.tools) and llm_request.tool_choice not in UNFORCED_TOOL_CHOICES
    if is_forced:
        announce(STATUS_FETCHING, callback_context.runtime)
    elif callback_context.tool_round == 0 or callback_context.text_is_reply:
        announce(STATUS_RESPONDING, callback_context.runtime)
