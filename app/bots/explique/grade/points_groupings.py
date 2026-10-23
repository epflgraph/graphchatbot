from typing_extensions import Self

from app.bots.explique.grade.explique_bot import ExpliqueGradeBot
from app.bots.explique.grade.topic_points import cache_extracted_points, extract_points
from app.bots.explique.grade.topics import Topic
from app.interfaces.moodle import MoodleClient, MoodleGrouping, moodle
from app.utils import collapse_whitespace


class PointsGroupings:
    """A course's topic points as its professors review and edit them: one Moodle grouping per topic, its description
    the points, written however the professors like. Students never see a grouping."""

    NAME = "Explique points: {topic}"

    def __init__(
        self, bot: ExpliqueGradeBot, groupings_by_name: dict[str, MoodleGrouping], *, client: MoodleClient = moodle
    ):
        self.bot = bot
        self.groupings_by_name = groupings_by_name
        self.client = client

    @classmethod
    async def fetch(cls, bot: ExpliqueGradeBot, *, client: MoodleClient = moodle) -> Self:
        """Every grouping in `bot`'s course, in one call."""
        return cls(bot, await client.get_groupings_by_name(bot.course_id), client=client)

    def is_blank(self, topic_name: str) -> bool:
        """Whether `topic_name` has no grouping, or one with nothing written in it."""
        return not self._get_description(topic_name).strip()

    async def get_points(self, topic_name: str) -> tuple[str, ...]:
        """The points in `topic_name`'s grouping, however they are written; none when it is blank."""
        description = self._get_description(topic_name)
        return await extract_points(self.bot, Topic(name=topic_name), description) if description.strip() else ()

    async def write_points(self, topic_name: str, points: tuple[str, ...]) -> None:
        """Put `points` in `topic_name`'s grouping, one per line behind a dash, creating the grouping when it has
        none."""
        description = "\n".join(f"- {point}" for point in points)
        if grouping := self._find_topic_grouping(topic_name):
            await self.client.update_grouping_description(grouping, description)
        else:
            await self.client.create_grouping(self.bot.course_id, self.NAME.format(topic=topic_name), description)

        # So the next pass reads `points` back without a model.
        cache_extracted_points(self.bot, Topic(name=topic_name), description, points)

    def _get_description(self, topic_name: str) -> str:
        """What `topic_name`'s grouping says; nothing when it has no grouping."""
        grouping = self._find_topic_grouping(topic_name)
        return grouping.description if grouping else ""

    def _find_topic_grouping(self, topic_name: str) -> MoodleGrouping | None:
        """`topic_name`'s grouping, matched the way `get_groupings_by_name` keys it."""
        return self.groupings_by_name.get(collapse_whitespace(self.NAME.format(topic=topic_name)).casefold())
