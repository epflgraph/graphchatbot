from collections.abc import Iterable, Iterator

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from app.bots.explique.utils import collapse_whitespace


class Topic(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)


class Topics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    topics: tuple[Topic, ...] = ()

    @classmethod
    def from_names(cls, topic_names: Iterable[str]) -> Self:
        """Deduped on case and spacing, blanks ignored — the first spelling of each wins."""
        by_name = {}
        for name in topic_names:
            if name.strip():
                by_name.setdefault(collapse_whitespace(name).casefold(), name)
        return cls(topics=tuple(Topic(name=name) for name in by_name.values()))

    @model_validator(mode="after")
    def _topic_names_are_unique(self) -> Self:
        seen = set()
        for topic in self.topics:
            normalized_name = collapse_whitespace(topic.name).casefold()
            if normalized_name in seen:
                raise ValueError(f"Duplicate topic names detected: {normalized_name!r}")
            seen.add(normalized_name)
        return self

    def __iter__(self) -> Iterator[Topic]:
        return iter(self.topics)

    def __len__(self) -> int:
        return len(self.topics)

    def __getitem__(self, position: int) -> Topic:
        return self.topics[position]

    def get_by_name(self, topic_name: str) -> Topic | None:
        """Seek a topic by name, case-insensitively and ignoring whitespace."""
        topic_name = collapse_whitespace(topic_name).casefold()
        for topic in self.topics:
            if collapse_whitespace(topic.name).casefold() == topic_name:
                return topic
        return None

    def get_by_number(self, topic_number: int) -> Topic | None:
        """Seek a topic by its index, counting from one."""
        return self[topic_number - 1] if 1 <= topic_number <= len(self) else None
