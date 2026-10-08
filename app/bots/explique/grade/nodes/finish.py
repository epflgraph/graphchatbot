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
from app.bots.explique.grade.nodes.revision import revision_node
from app.bots.explique.grade.prompts import (
    FINISH_CLOSED_TEMPLATE,
    FINISH_NEW_CHAT_TEMPLATE,
    FINISH_RETRY_TEMPLATE,
    FINISH_REVISION_TEMPLATE,
    FINISH_TEMPLATE,
    STATUS_FINISHING_TEMPLATE,
)
from app.bots.explique.grade.state import GradeBotState
from app.bots.explique.grade.transcript import graded_turns
from app.bots.explique.nodes.summarize import summarize_node
from app.bots.graph_chat.graph_chat_bot import GraphChatBot
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
    recorder = CoverageRecorder(bot.course_id, state["requester"])
    # The session recap and coverage recording share nothing, so the LLM calls and the Moodle
    # round trips overlap. Only the recording decides what the student is told about
    # the quiz; the recap is decorative.
    # The recap reads the explanation only, as the graders do: turns before the lock are the student
    # finding a topic, not working on one, and grading them reads as grading the menu.
    session_messages = graded_turns(bot.prompt_search_path, topic, topic_lock.post_lock_turns(state["messages"]))
    session_state = {**state, "messages": session_messages}
    async with asyncio.TaskGroup() as tasks:
        summarizing = tasks.create_task(summarize_node(session_state, runtime))
        revising = tasks.create_task(revision_node(session_state, runtime))
        access = await recorder.record(topic, on_retry=partial(_announce_retry, runtime))
        closing = render_prompt(
            bot.prompt_search_path,
            FINISH_TEMPLATE,
            topic=topic,
            access=access,
            finish_marker=finish_marker(bot.prompt_search_path, state.get("lang_code")),
            lang_code=state.get("lang_code"),
        )
        await stream_text(f"{closing}\n\n", runtime.stream_writer)
        announce(STATUS_FINISHING_TEMPLATE, runtime)

    summary = summarizing.result()["session_summary"]
    revision = revising.result()["revision"]

    feedback = await text_call(
        bot,
        GradeFeedbackCompiler,
        {**state, "session_summary": summary},
        tags=(TAG_NOSTREAM,),
        fallback="",
        stream_writer=runtime.stream_writer,
    )

    revision_section = render_prompt(
        bot.prompt_search_path,
        FINISH_REVISION_TEMPLATE,
        revision=revision,
        review_model=GraphChatBot.name,
        lang_code=state.get("lang_code"),
    )
    new_chat = render_prompt(bot.prompt_search_path, FINISH_NEW_CHAT_TEMPLATE, lang_code=state.get("lang_code"))
    after_feedback = "\n\n".join(part for part in (revision_section, new_chat) if part)
    await stream_text(f"\n\n{after_feedback}" if feedback else after_feedback, runtime.stream_writer)
    return {
        "messages": [
            AIMessage(content="\n\n".join(part for part in (closing, feedback, revision_section, new_chat) if part))
        ],
        "session_summary": summary,
        "revision": revision,
    }
