from enum import StrEnum


class TrainNode(StrEnum):
    """The nodes only the tutor's graph runs, on top of the `Node` ones."""

    PRACTICE = "practice"
    SUMMARIZE = "summarize"
