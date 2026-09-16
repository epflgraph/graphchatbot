import asyncio
import logging
from functools import partial

from langchain_core.messages import AIMessage
from langgraph.constants import TAG_NOSTREAM
from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.grade.compilers.feedback import GradeFeedbackCompiler
from app.bots.explique.grade.completion import finish_marker
from app.bots.explique.grade.coverage_record import CoverageRecorder
from app.bots.explique.grade.prompts import (
    FINISH_CLOSED_TEMPLATE,
    FINISH_RETRY_TEMPLATE,
    FINISH_TEMPLATE,
    STATUS_FINISHING_TEMPLATE,
)
from app.bots.explique.grade.state import GradeBotState
from app.bots.explique.nodes.summarize import summarize_node
from app.bots.utils import announce, stream_text
from app.compilation.invoke import text_call
from app.compilation.templates import render_prompt

logger = logging.getLogger(__name__)


def _announce_retry(runtime: Runtime[Bot], retry_number: int) -> None:
    """Announce recording retries, as events."""
    announce(FINISH_RETRY_TEMPLATE, runtime, retry_attempt=retry_number)


async def finish_node(state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Close the exercise: recap the session, record the coverage, hand over the quiz.

    The closing message carries the marker `session_finished` reads, so the exercise ends
    here whether or not the recording succeeds; a recording that never lands says so."""
    bot = runtime.context
    topic_lock = state["topic_lock"]

    if state["session_finished"]:
        topic = topic_lock.topic if topic_lock else None
        closed = render_prompt(
            bot.prompt_search_path, FINISH_CLOSED_TEMPLATE, topic=topic, lang_code=state.get("lang_code")
        )
        await stream_text(closed, runtime.stream_writer)
        return {"messages": [AIMessage(content=closed)]}

    topic = topic_lock.topic
    logger.info("Topic covered, finishing: %s", topic.name)
    announce(STATUS_FINISHING_TEMPLATE, runtime)
    recorder = CoverageRecorder(bot.course_id, state["requester"])
    # The session recap and coverage recording share nothing, so the LLM call and the Moodle
    # round trips overlap. Only the recording decides what the student is told about
    # the quiz; the recap is decorative.
    # The recap reads the explanation only: turns before the lock are the student
    # finding a topic, not working on one, and grading them reads as grading the menu.
    session_messages = topic_lock.post_lock_turns(state["messages"])
    updated_state, access = await asyncio.gather(
        summarize_node({**state, "messages": session_messages}, runtime),
        recorder.record(topic, on_retry=partial(_announce_retry, runtime)),
    )

    summary = updated_state["session_summary"]

    feedback = await text_call(
        bot,
        GradeFeedbackCompiler,
        {**state, "session_summary": summary},
        tags=(TAG_NOSTREAM,),
        fallback="",
        stream_writer=runtime.stream_writer,
    )

    closing = render_prompt(
        bot.prompt_search_path,
        FINISH_TEMPLATE,
        topic=topic,
        access=access,
        finish_marker=finish_marker(bot.prompt_search_path, state.get("lang_code")),
        lang_code=state.get("lang_code"),
    )
    await stream_text(f"\n\n{closing}", runtime.stream_writer)
    return {
        "messages": [AIMessage(content=f"{feedback}\n\n{closing}".strip())],
        "session_summary": summary,
    }
