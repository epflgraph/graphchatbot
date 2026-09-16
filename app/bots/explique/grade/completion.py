from pathlib import Path

from langchain_core.messages import BaseMessage

from app.bots.explique.grade.models import GradeChallengePlan
from app.bots.explique.grade.prompts import FINISH_MARKER_TEMPLATE
from app.bots.explique.models import StudentState
from app.bots.languages import LANGUAGES
from app.compilation.templates import render_prompt
from app.llms.utils import flatten_content

# The minimum explaining turns a topic must take before it can count as covered.
MIN_EXPLAINING_TURNS = 5


def finish_marker(search_path: tuple[Path, ...], lang_code: str | None) -> str:
    """The closing sentence to write, in the language the session is in."""
    return render_prompt(search_path, FINISH_MARKER_TEMPLATE, lang_code=lang_code)


def session_finished(search_path: tuple[Path, ...], messages: list[BaseMessage]) -> bool:
    """Whether this transcript already carries a closing marker, in any language."""
    markers = {finish_marker(search_path, lang_code) for lang_code in LANGUAGES}
    return any(
        marker in flatten_content(message.content) for message in messages if message.type == "ai" for marker in markers
    )


def topic_covered(plan: GradeChallengePlan | None, student_state: StudentState, explaining_turns: int) -> bool:
    """Whether the topic is covered, and the quiz should open."""
    if plan is None or not plan.topic_exhausted:
        return False

    if not student_state.mastery:
        return False

    return explaining_turns >= MIN_EXPLAINING_TURNS
