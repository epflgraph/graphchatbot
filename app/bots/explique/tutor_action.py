from enum import StrEnum

from app.bots.explique.models import EngagementLevel, GapSeverity, GapType, Persistence, StudentState


class TutorAction(StrEnum):
    MOTIVATE = "motivate"
    PROBE = "probe"
    HINT = "hint"
    EXPLAIN = "explain"
    CHALLENGE_MISCONCEPTION = "challenge-misconception"
    CHALLENGE_MASTERY = "challenge-mastery"


# What CHALLENGE_MISCONCEPTION refutes: an active wrong belief the student can
# be handed back and asked to defend — not just an absence of knowledge. That
# excludes `domain` even though it's always-substantive below (nothing wrong
# was asserted, just something unknown) and `procedural` (right idea, bad
# mechanics — see _needs_hint). `transient` is deliberately absent too:
# genuine flailing has nothing to refute.
_CHALLENGEABLE_GAP_TYPES = frozenset(
    {
        GapType.CONCEPTUAL,
        GapType.LOGICAL,
        GapType.BIAS,
    }
)

# Gap types that reflect a genuine, durable understanding problem, so they
# call for an explanation regardless of severity. `procedural` (mechanics
# only) and `transient` (noise/flailing) are excluded — a partial instance of
# either is assumed to resolve on its own, and only counts as substantive via
# the `_is_large_gap` branch of `_is_substantive_gap`.
_ALWAYS_SUBSTANTIVE_GAP_TYPES = frozenset(
    {
        GapType.CONCEPTUAL,
        GapType.DOMAIN,
        GapType.LOGICAL,
        GapType.BIAS,
    }
)


# ----- pedagogical conditions ------------------------------------------


def _is_disengaged(student_state: StudentState) -> bool:
    return student_state.engagement_level == EngagementLevel.LOW


def _is_large_gap(student_state: StudentState) -> bool:
    return student_state.gap_severity == GapSeverity.LARGE


def _is_stalled(student_state: StudentState) -> bool:
    return student_state.persistence == Persistence.STALLED


def _is_challengeable(student_state: StudentState) -> bool:
    return student_state.gap_type in _CHALLENGEABLE_GAP_TYPES


def _is_substantive_gap(student_state: StudentState) -> bool:
    """A large gap of any type, or one of the always-substantive types. These
    are the gaps that ultimately call for an explanation."""
    return _is_large_gap(student_state) or student_state.gap_type in _ALWAYS_SUBSTANTIVE_GAP_TYPES


def _is_ready_to_be_taught(student_state: StudentState) -> bool:
    """The precondition every teaching move shares: there is something to teach,
    and someone listening."""
    return not student_state.mastery and not _is_disengaged(student_state)


# --- the rules ----------------------------------------------------------


def _needs_mastery_challenge(student_state: StudentState) -> bool:
    """A correct explanation is never taken at face value: it is always
    perturbed with a mastery challenge."""
    return student_state.mastery


def _needs_motivation(student_state: StudentState) -> bool:
    """A disengaged student needs re-engagement before any teaching move."""
    return not student_state.mastery and _is_disengaged(student_state)


def _needs_explanation(student_state: StudentState) -> bool:
    """Substantive gaps ultimately call for an explanation, but we withhold it to
    keep the dialogue Socratic: the student must reason first, and only earns one
    once they are genuinely stalled on the same point with no way out. This is
    the single route to a direct answer."""
    return _is_ready_to_be_taught(student_state) and _is_substantive_gap(student_state) and _is_stalled(student_state)


def _needs_misconception_challenge(student_state: StudentState) -> bool:
    """A committed wrong belief is refuted by presenting it back, not by probing
    around it — regardless of severity, since a large, confidently-held
    misconception is the prime challenge target, but only while the student
    hasn't stalled on it."""
    return (
        _is_ready_to_be_taught(student_state)
        and _is_substantive_gap(student_state)
        and not _is_stalled(student_state)
        and _is_challengeable(student_state)
    )


def _needs_hint(student_state: StudentState) -> bool:
    """Right idea, wrong mechanics: nudged toward the next step rather than
    probed, regardless of severity — unless the gap is both large and the
    student has stalled on it."""
    return (
        _is_ready_to_be_taught(student_state)
        and student_state.gap_type == GapType.PROCEDURAL
        and not (_is_substantive_gap(student_state) and _is_stalled(student_state))
    )


# Reads naturally top-to-bottom, but isn't load-bearing: the conditions above
# are already mutually exclusive, so any order would pick the same action.
_RULES = (
    (_needs_mastery_challenge, TutorAction.CHALLENGE_MASTERY),
    (_needs_motivation, TutorAction.MOTIVATE),
    (_needs_explanation, TutorAction.EXPLAIN),
    (_needs_misconception_challenge, TutorAction.CHALLENGE_MISCONCEPTION),
    (_needs_hint, TutorAction.HINT),
)


def select_tutor_action(student_state: StudentState) -> TutorAction:
    """The move an evaluated state calls for.

    `probe` is the default rather than a rule of its own: it is what a transient
    gap gets, and the safety net for any state the rules above do not claim.
    """
    for applies, action in _RULES:
        if applies(student_state):
            return action
    return TutorAction.PROBE
