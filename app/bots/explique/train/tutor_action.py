from functools import partial

from app.bots.explique.models import GapType, StudentState, TutorAction
from app.bots.explique.tutor_action import (
    is_ready_to_be_taught,
    is_stalled,
    is_substantive_gap,
    needs_mastery_challenge,
    needs_misconception_challenge,
    needs_motivation,
    select_by_rules,
)


def _needs_explanation(student_state: StudentState) -> bool:
    """Substantive gaps ultimately call for an explanation, but we withhold it to
    keep the dialogue Socratic: the student must reason first, and only earns one
    once they are genuinely stalled on the same point with no way out. This is
    the single route to a direct answer."""
    return is_ready_to_be_taught(student_state) and is_substantive_gap(student_state) and is_stalled(student_state)


def _needs_hint(student_state: StudentState) -> bool:
    """Right idea, wrong mechanics: nudged toward the next step rather than
    probed, regardless of severity — unless the gap is both large and the
    student has stalled on it."""
    return (
        is_ready_to_be_taught(student_state)
        and student_state.gap_type == GapType.PROCEDURAL
        and not (is_substantive_gap(student_state) and is_stalled(student_state))
    )


# Reads naturally top-to-bottom, but isn't load-bearing: the conditions are
# mutually exclusive, so any order would pick the same action.
RULES = (
    (needs_mastery_challenge, TutorAction.CHALLENGE_MASTERY),
    (needs_motivation, TutorAction.MOTIVATE),
    (_needs_explanation, TutorAction.EXPLAIN),
    (needs_misconception_challenge, TutorAction.CHALLENGE_MISCONCEPTION),
    (_needs_hint, TutorAction.HINT),
)

select_tutor_action = partial(select_by_rules, RULES)
