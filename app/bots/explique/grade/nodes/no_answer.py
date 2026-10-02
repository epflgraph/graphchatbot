from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.grade.state import GradeBotState
from app.bots.languages import no_answer
from app.bots.utils import stream_text


async def no_answer_node(state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Answer a turn that could not be graded with a canned apology."""
    no_ans = no_answer(runtime.context.prompt_search_path, state.get("lang_code"))
    await stream_text(no_ans, runtime.stream_writer)
    return {"messages": [AIMessage(content=no_ans)]}
