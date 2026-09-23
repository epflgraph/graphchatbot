from pathlib import Path

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ConfigDict

from app.bots.explique.grade.prompts import INVITE_TEMPLATE, TOPIC_LIST_TEMPLATE
from app.bots.explique.grade.topics import Topic, Topics
from app.bots.explique.grade.transcript import graded_turns, text_after_attachment
from app.bots.explique.grade.utils import parse_int
from app.bots.languages import LANGUAGES
from app.compilation.templates import render_prompt
from app.llms.utils import flatten_content


class TopicLock(BaseModel):
    """Where a transcript picked its topic, and which one."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    position: int
    topic: Topic

    def is_in_latest_turn(self, messages: list[BaseMessage]) -> bool:
        """Whether the topic lock happened in the last turn of `messages`."""
        return self.position == len(messages) - 1

    def post_lock_turns(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """The turns that followed the topic lock."""
        return messages[self.position + 1 :]

    def explaining_turns(self, search_path: tuple[Path, ...], messages: list[BaseMessage]) -> int:
        """How many turns the student has spent explaining their locked topic."""
        graded = graded_turns(search_path, self.topic, self.post_lock_turns(messages))
        return sum(1 for message in graded if message.type == "human")


def has_invitation_for_topic(search_path: tuple[Path, ...], message: BaseMessage, topic: Topic) -> bool:
    """Whether a given assistant turn is an invitation for `topic` discussion."""
    content = flatten_content(message.content)
    return any(
        content.startswith(render_prompt(search_path, INVITE_TEMPLATE, topic=topic, lang_code=lang_code))
        for lang_code in LANGUAGES
    )


def _selected_topic(topics: Topics, content: str, by_number: bool) -> Topic | None:
    """The topic this student turn selects, by name or, when `by_number`, by its number on the menu."""
    if topic := topics.get_by_name(content):
        return topic

    topic_number = parse_int(content) if by_number else None
    return topics.get_by_number(topic_number) if topic_number is not None else None


def find_topic_lock(search_path: tuple[Path, ...], topics: Topics, messages: list[BaseMessage]) -> TopicLock | None:
    """Where this transcript locked its topic, and to what: the first student turn to select one.

    A selection counts only once the bot replied with an invitation.
    """
    topic_list = render_prompt(search_path, TOPIC_LIST_TEMPLATE, topics=topics)
    menu_is_current = False
    for position, message in enumerate(messages):
        # Whether what the student is answering still lists the topics now on offer
        if message.type == "ai":
            menu_is_current = topic_list in flatten_content(message.content)
            continue

        # We don't care about other roles (e.g tool)
        if message.type != "human":
            continue

        # A new number needs a current menu, or "3" could lock a topic the student never saw.
        # An earlier one is checked against the invitation that answered it instead.
        is_latest_turn = position == len(messages) - 1
        content = flatten_content(message.content)
        after_file = text_after_attachment(content)
        topic = _selected_topic(
            topics, content if after_file is None else after_file, by_number=menu_is_current or not is_latest_turn
        )
        if topic is None:
            continue

        # If topic selection happens in the last turn, then it counts as a lock
        if is_latest_turn:
            return TopicLock(position=position, topic=topic)

        next_turn = messages[position + 1]
        if next_turn.type == "ai" and has_invitation_for_topic(search_path, next_turn, topic):
            return TopicLock(position=position, topic=topic)

    return None
