from functools import partial

from app.bots.explique.models import GapType, StudentState, TutorAction
from app.bots.explique.tutor_action import (
    is_ready_to_be_taught,
    is_stalled,
    needs_mastery_challenge,
    needs_misconception_challenge,
    needs_motivation,
    select_by_rules,
)


def _needs_motivation(student_state: StudentState) -> bool:
    """A disengaged student is re-engaged before any teaching move, unless they have stalled: their attempts earned
    the explanation, and frustration by then is no reason to withhold it."""
    return needs_motivation(student_state) and not is_stalled(student_state)


def _needs_explanation(student_state: StudentState) -> bool:
    """We withhold an explanation to keep the dialogue Socratic: the student must reason
    first, and only earns one once they are genuinely stalled on the same point, whatever
    the size of the gap or their mood by then. This is the single route to a direct answer, and the planner
    credits the explained point only on a later case."""
    return not student_state.mastery and is_stalled(student_state)


def _needs_hint(student_state: StudentState) -> bool:
    """Right idea wrong mechanics, while the student has not stalled; once they have, they get the explanation."""
    return (
        is_ready_to_be_taught(student_state)
        and student_state.gap_type == GapType.PROCEDURAL
        and not is_stalled(student_state)
    )


# Reads naturally top-to-bottom, but isn't load-bearing: the conditions are
# mutually exclusive, so any order would pick the same action.
RULES = (
    (needs_mastery_challenge, TutorAction.CHALLENGE_MASTERY),
    (_needs_motivation, TutorAction.MOTIVATE),
    (_needs_explanation, TutorAction.EXPLAIN),
    (needs_misconception_challenge, TutorAction.CHALLENGE_MISCONCEPTION),
    (_needs_hint, TutorAction.HINT),
)

select_tutor_action = partial(select_by_rules, RULES)
