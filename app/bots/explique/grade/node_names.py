from enum import StrEnum


class GradeNode(StrEnum):
    """The nodes only the grader's graph runs, on top of the `Node` ones."""

    LOCK_TOPIC = "lock_topic"
    DERIVE_TOPIC_POINTS = "derive_topic_points"
    PRESENT_MENU = "present_menu"
    INVITE = "invite"
    POST_CLASSIFY = "post_classify"
    REDIRECT = "redirect"
    FINISH = "finish"
    NO_ANSWER = "no_answer"
