from enum import StrEnum


class Node(StrEnum):
    """The graph nodes both explique flavours run, named in one place."""

    TRANSCRIBE_IMAGE = "transcribe_image"
    DETECT_LANGUAGE = "detect_language"
    CLASSIFY = "classify"
    RETRIEVE = "retrieve"
    TOOLS = "tools"
    POST_RETRIEVE = "post_retrieve"
    EVALUATE = "evaluate"
    PLAN_CHALLENGE = "plan_challenge"
    SELECT_ACTION = "select_action"
    RESPOND = "respond"
    EVALUATE_RESPONSE = "evaluate_response"
