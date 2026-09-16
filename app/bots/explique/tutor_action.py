from collections.abc import Callable

from app.bots.explique.models import EngagementLevel, GapSeverity, GapType, Persistence, StudentState, TutorAction

# One rule: the condition, and the move it selects.
Rule = tuple[Callable[[StudentState], bool], TutorAction]

# What CHALLENGE_MISCONCEPTION refutes: an active wrong belief the student can be handed
# back and asked to defend, not just an absence of knowledge. That excludes `domain` even
# though it is always substantive below (nothing wrong was asserted, just something unknown)
# and `procedural` (right idea, bad mechanics). `transient` is absent too: genuine flailing
# has nothing to refute.
CHALLENGEABLE_GAP_TYPES = frozenset({GapType.CONCEPTUAL, GapType.LOGICAL, GapType.BIAS})

# Gap types that reflect a genuine, durable understanding problem. `procedural` (mechanics
# only) and `transient` (noise/flailing) are excluded: neither is a settled belief, so
# either one counts as substantive only when the gap is large.
ALWAYS_SUBSTANTIVE_GAP_TYPES = frozenset({GapType.CONCEPTUAL, GapType.DOMAIN, GapType.LOGICAL, GapType.BIAS})


# ----- pedagogical conditions ------------------------------------------


def is_disengaged(student_state: StudentState) -> bool:
    return student_state.engagement_level == EngagementLevel.LOW


def is_large_gap(student_state: StudentState) -> bool:
    return student_state.gap_severity == GapSeverity.LARGE


def is_stalled(student_state: StudentState) -> bool:
    return student_state.persistence == Persistence.STALLED


def is_challengeable(student_state: StudentState) -> bool:
    return student_state.gap_type in CHALLENGEABLE_GAP_TYPES


def is_substantive_gap(student_state: StudentState) -> bool:
    """A large gap of any type, or one of the always-substantive types."""
    return is_large_gap(student_state) or student_state.gap_type in ALWAYS_SUBSTANTIVE_GAP_TYPES


def is_ready_to_be_taught(student_state: StudentState) -> bool:
    """The precondition every teaching move shares: something to teach, and someone listening."""
    return not student_state.mastery and not is_disengaged(student_state)


# ----- the rules both flavours share --------------------------------------


def needs_mastery_challenge(student_state: StudentState) -> bool:
    """A correct explanation is never taken at face value: it is always perturbed."""
    return student_state.mastery


def needs_motivation(student_state: StudentState) -> bool:
    """A disengaged student needs re-engagement before any teaching move."""
    return not student_state.mastery and is_disengaged(student_state)


def needs_misconception_challenge(student_state: StudentState) -> bool:
    """A committed wrong belief is refuted by presenting it back, not by probing around it,
    whatever its severity, but only while the student has not stalled on it."""
    return (
        is_ready_to_be_taught(student_state)
        and is_substantive_gap(student_state)
        and not is_stalled(student_state)
        and is_challengeable(student_state)
    )


def select_by_rules(rules: tuple[Rule, ...], student_state: StudentState) -> TutorAction:
    """The move `rules` call for. `probe` is the default rather than a rule: it is what a
    transient gap gets, and the safety net for any state the rules leave unclaimed."""
    for applies, action in rules:
        if applies(student_state):
            return action
    return TutorAction.PROBE
