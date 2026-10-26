import logging
import secrets

from langchain_core.messages import AIMessage

from app.bots.callbacks.base import CallbackContext

logger = logging.getLogger(__name__)


async def fill_missing_call_ids(callback_context: CallbackContext, llm_response: AIMessage) -> None:
    """Gives a random id to every call missing one.

    https://github.com/langchain-ai/langgraph/issues/4717
    """
    for call in llm_response.tool_calls:
        if not call["id"]:
            logger.warning("Missing tool call id, fixing with random string.")
            call["id"] = f"chatcmpl-tool-{secrets.token_hex(16)}"


async def fix_repeated_tool_names(callback_context: CallbackContext, llm_response: AIMessage) -> None:
    """Fixes a doubled tool name, e.g. 'search_lexsearch_lex' → 'search_lex'."""
    tool_names = [tool.name for tool in callback_context.tools]
    for call in llm_response.tool_calls:
        if call["name"] in tool_names:
            continue
        for name in tool_names:
            if name in call["name"]:
                logger.warning("Fixing repeated tool name `%s` → `%s`.", call["name"], name)
                call["name"] = name
                break
