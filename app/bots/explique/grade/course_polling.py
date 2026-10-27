import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from operator import attrgetter

from app.bots.base import Bot
from app.bots.explique.grade.coverage_record import ASSESSMENT_ACTIVITY_TYPES, TOPIC_GROUP_NAME
from app.bots.explique.grade.explique_bot import ExpliqueGradeBot
from app.bots.explique.grade.points_groupings import PointsGroupings
from app.bots.explique.grade.topic_points import TopicPointsUnavailable, derive_topic_points
from app.bots.explique.grade.topics import Topic, Topics
from app.interfaces.moodle import MoodleClient, MoodleError, MoodleModule, moodle
from app.logging_config import truncate
from app.utils import collapse_whitespace

logger = logging.getLogger(__name__)

# What the professor writes in an activity's title to say which topic it belongs to, case ignored.
TOPIC_TAG = re.compile(r"\[TOPIC:([^\[\]]*)\]", re.IGNORECASE)


def topics_in_activity_title(title: str) -> tuple[str, ...]:
    """The topics `title` is tagged with, in the order written, each one kept once."""
    names = []
    lookup = set()

    for name in TOPIC_TAG.findall(title):
        normalized = collapse_whitespace(name).casefold()
        if normalized and normalized not in lookup:
            lookup.add(normalized)
            names.append(name.strip())

    return tuple(names)


@dataclass(frozen=True)
class TaggedTopic:
    """A topic tagged on a course's activities, and every activity carrying it."""

    name: str
    activities: tuple[MoodleModule, ...]

    @property
    def visible(self) -> bool:
        """Whether a student can see any of the activities carrying this topic."""
        return any(activity.visible for activity in self.activities)

    @property
    def closes_at(self) -> datetime | None:
        """When the last visible activity carrying this topic closes; None while any of them stays open."""
        close_dates = [activity.closes_at for activity in self.activities if activity.visible]
        if not close_dates or None in close_dates:
            return None
        return max(close_dates)

    def is_restricted_to(self, group_id: int) -> bool:
        """Whether any activity carrying this topic is restricted to `group_id`."""
        return any(group_id in activity.restriction_group_ids() for activity in self.activities)


def _tagged_topics(modules: list[MoodleModule]) -> tuple[TaggedTopic, ...]:
    """Every topic the course's assessment activities are tagged with, in ascending order of creation."""
    # Both keyed on the normalized name.
    topic_names = {}
    activities = {}

    # Oldest first, by Moodle id, which grows as activities are created.
    for module in sorted(modules, key=attrgetter("id")):
        if module.modname not in ASSESSMENT_ACTIVITY_TYPES:
            continue

        for topic in topics_in_activity_title(module.name or ""):
            key = collapse_whitespace(topic).casefold()
            topic_names.setdefault(key, topic)
            activities.setdefault(key, []).append(module)

    return tuple(TaggedTopic(name=name, activities=tuple(activities[key])) for key, name in topic_names.items())


class CoursePoller:
    """Keeps one graded bot's course set up, one pass at a time: its topics published to the bot, each with a group
    for its quiz to restrict to and a points grouping its professors can edit, holding that group."""

    def __init__(self, bot: ExpliqueGradeBot, *, client: MoodleClient = moodle):
        self.bot = bot
        self.client = client
        # What was last logged.
        self._reported_points_groupings_error: str | None = None
        self._reported_groups_in_groupings_error: str | None = None
        self._reported_fill_errors: dict[str, str] = {}
        self._reported_unrestricted_topics: tuple[str, ...] = ()

    async def run(self) -> None:
        tagged_topics = await self._fetch_tagged_topics()
        points_groupings = await self._fetch_points_groupings()
        await self._publish_topics(tagged_topics, points_groupings)
        group_ids_by_topic = await self._find_or_create_groups(tagged_topics)
        self._report_unrestricted_topics(tagged_topics, group_ids_by_topic)
        if points_groupings is not None:
            await self._fill_points_groupings(tagged_topics, points_groupings)
            await self._add_groups_to_points_groupings(group_ids_by_topic, points_groupings)

    async def _fetch_tagged_topics(self) -> tuple[TaggedTopic, ...]:
        """The whole course, narrowed to the assessments whose title carries a `[TOPIC: ...]` tag."""
        return _tagged_topics(await self.client.get_course_modules(self.bot.course_id))

    async def _publish_topics(
        self, tagged_topics: tuple[TaggedTopic, ...], points_groupings: PointsGroupings | None
    ) -> None:
        """Offer students every topic they can see, with the points its professors left in its grouping."""
        # Only reached once the course was read: a failed pass raises before here, so an outage leaves the last
        # good menu standing rather than nuking it.
        self.bot.topics = Topics(
            topics=[
                Topic(
                    name=topic.name,
                    deadline=topic.closes_at,
                    points=await self._get_points(topic.name, points_groupings),
                )
                for topic in tagged_topics
                if topic.visible
            ]
        )

    async def _find_or_create_groups(self, tagged_topics: tuple[TaggedTopic, ...]) -> dict[str, int]:
        """The id of every tagged topic's group by topic name, creating the ones nobody has made; a topic whose group
        Moodle refuses to create is left out."""
        # Every group the course has, in one call. Read every pass so a deleted group is recreated and reported.
        group_ids_by_name = await self.client.get_group_ids_by_name(self.bot.course_id)

        group_ids_by_topic = {}
        for topic in tagged_topics:
            group_id = await self._find_or_create_group(topic, group_ids_by_name)
            if group_id is not None:
                group_ids_by_topic[topic.name] = group_id

        return group_ids_by_topic

    async def _find_or_create_group(self, topic: TaggedTopic, group_ids_by_name: dict[str, int]) -> int | None:
        """The id of `topic`'s group, created when nobody has made it; None when Moodle refuses to create it."""
        # Named the way a finished session looks it up, so it finds this group
        # rather than a second one spelled differently.
        group_name = TOPIC_GROUP_NAME.format(topic=topic.name)
        group_id = group_ids_by_name.get(collapse_whitespace(group_name).casefold())
        if group_id is not None:
            return group_id

        # Nobody has made it: the group is explique's own, so make it here.
        try:
            group_id = await self.client.create_group(self.bot.course_id, group_name)
        except MoodleError:
            # One refused topic must not stop the others.
            logger.warning(
                "Could not create group for topic %r in course %s", topic.name, self.bot.course_id, exc_info=True
            )
            return None

        logger.info("Created group for topic %r in course %s (%s)", topic.name, self.bot.course_id, self.bot.name)
        return group_id

    def _report_unrestricted_topics(
        self, tagged_topics: tuple[TaggedTopic, ...], group_ids_by_topic: dict[str, int]
    ) -> None:
        """Log the topics whose quiz is not restricted to their group yet, when they changed since last logged."""
        unrestricted_topics = tuple(
            topic.name
            for topic in tagged_topics
            if topic.name in group_ids_by_topic and not topic.is_restricted_to(group_ids_by_topic[topic.name])
        )
        if unrestricted_topics == self._reported_unrestricted_topics:
            return

        if unrestricted_topics:
            logger.info(
                "Course %s has %s topic(s) whose quiz is not restricted to their group yet: %s",
                self.bot.course_id,
                len(unrestricted_topics),
                ", ".join(unrestricted_topics),
            )
        else:
            logger.info("Course %s has every tagged quiz restricted", self.bot.course_id)
        self._reported_unrestricted_topics = unrestricted_topics

    async def _fetch_points_groupings(self) -> PointsGroupings | None:
        """The course's points groupings, or None if Moodle doesn't list them."""
        try:
            points_groupings = await PointsGroupings.fetch(self.bot, client=self.client)
        except MoodleError as error:
            self._report_points_groupings_error(str(error))
            return None

        self._report_points_groupings_error(None)
        return points_groupings

    def _report_points_groupings_error(self, error: str | None) -> None:
        """Log why the groupings can't be read, or that they can again, when it changed since last logged."""
        if error == self._reported_points_groupings_error:
            return

        if error:
            logger.warning(
                "Could not read the groupings of course %s (%s), so its topics keep the points last read: %s",
                self.bot.course_id,
                self.bot.name,
                truncate(error),
            )
        else:
            logger.info("Course %s has its groupings readable again", self.bot.course_id)
        self._reported_points_groupings_error = error

    async def _get_points(self, topic_name: str, points_groupings: PointsGroupings | None) -> tuple[str, ...]:
        """The points in `topic_name`'s grouping, or the ones published last pass if the grouping can't be read."""
        if points_groupings is not None:
            try:
                return await points_groupings.get_points(topic_name)
            except TopicPointsUnavailable:
                logger.warning(
                    "Could not read the points grouping of topic %r in course %s; keeping last pass's points",
                    topic_name,
                    self.bot.course_id,
                )

        published = self.bot.topics.get_by_name(topic_name)
        return published.points if published else ()

    async def _fill_points_groupings(
        self, tagged_topics: tuple[TaggedTopic, ...], points_groupings: PointsGroupings
    ) -> None:
        """Put the generated points in every tagged topic's grouping that is blank, so what its professors see is what
        grades. Hidden quizzes count too, so the points can be reviewed before students see the topic."""
        fill_errors = {}
        for topic in tagged_topics:
            if not points_groupings.is_blank(topic.name):
                continue

            try:
                # Reuses the points students are graded on, and waits out a failed search rather than keep points
                # from the name.
                points = await derive_topic_points(
                    self.bot, Topic(name=topic.name), reuse_saved=True, unsourced_on_failure=False
                )
                await points_groupings.write_points(topic.name, points)
            except (TopicPointsUnavailable, MoodleError) as error:
                # One topic must not stop the others; the next pass tries it again. Logged when the reason changes,
                # with no traceback, since the reason is in the error.
                fill_errors[topic.name] = repr(error)
                if fill_errors[topic.name] != self._reported_fill_errors.get(topic.name):
                    logger.warning(
                        "Could not fill the points grouping for topic %r in course %s: %s",
                        topic.name,
                        self.bot.course_id,
                        truncate(fill_errors[topic.name]),
                    )

        self._reported_fill_errors = fill_errors

    async def _add_groups_to_points_groupings(
        self, group_ids_by_topic: dict[str, int], points_groupings: PointsGroupings
    ) -> None:
        """Put every topic's group in its points grouping where it isn't, so Moodle shows the two together. A grouping
        created this pass gets its group on the next."""
        grouping_ids_by_topic = {
            topic_name: grouping.id
            for topic_name in group_ids_by_topic
            if (grouping := points_groupings.find_topic_grouping(topic_name))
        }
        if not grouping_ids_by_topic:
            return

        try:
            group_ids_by_grouping = await self.client.get_group_ids_by_grouping(list(grouping_ids_by_topic.values()))
        except MoodleError as error:
            self._report_groups_in_groupings_error(str(error))
            return

        add_error = None
        for topic_name, grouping_id in grouping_ids_by_topic.items():
            if group_ids_by_topic[topic_name] in group_ids_by_grouping.get(grouping_id, set()):
                continue

            try:
                await self.client.add_group_to_grouping(group_ids_by_topic[topic_name], grouping_id)
            except MoodleError as error:
                # One topic must not stop the others; the next pass tries it again.
                add_error = str(error)

        self._report_groups_in_groupings_error(add_error)

    def _report_groups_in_groupings_error(self, error: str | None) -> None:
        """Log why the topic groups can't be put in their points groupings, or that they can again, when it changed
        since last logged."""
        if error == self._reported_groups_in_groupings_error:
            return

        if error:
            logger.warning(
                "Could not put the topic groups in the points groupings of course %s (%s): %s",
                self.bot.course_id,
                self.bot.name,
                truncate(error),
            )
        else:
            logger.info("Course %s has its topic groups put in its points groupings again", self.bot.course_id)
        self._reported_groups_in_groupings_error = error


async def _poll_courses(
    bots: list[ExpliqueGradeBot], interval_seconds: float, *, client: MoodleClient = moodle
) -> None:
    """Poll every course forever. One course's failure never stops the others, or the loop."""
    pollers = [CoursePoller(bot, client=client) for bot in bots]
    logger.info("Polling %s course(s) for tagged quizzes every %ss", len(bots), interval_seconds)

    while True:
        for poller in pollers:
            bot = poller.bot
            try:
                await poller.run()
            except MoodleError:
                logger.warning("Moodle failed while polling course %s (%s)", bot.course_id, bot.name, exc_info=True)
            except Exception:
                logger.exception("Polling course %s (%s) failed", bot.course_id, bot.name)

        await asyncio.sleep(interval_seconds)


def _get_grade_bots(bots: list[Bot]) -> list[ExpliqueGradeBot]:
    return [bot for bot in bots if isinstance(bot, ExpliqueGradeBot)]


def start_polling(bots: list[Bot], *, interval_seconds: float, client: MoodleClient = moodle) -> asyncio.Task | None:
    """Start the polling task, or nothing when there is no course to poll or no Moodle configured."""
    grade_bots = _get_grade_bots(bots)
    if not grade_bots:
        logger.info("No graded bot is registered; nothing to poll")
        return None

    if not client.configured:
        logger.error(
            "Moodle is not configured, so %s graded bot(s) will offer no topics: %s",
            len(grade_bots),
            ", ".join(bot.name for bot in grade_bots),
        )
        return None

    return asyncio.create_task(_poll_courses(grade_bots, interval_seconds, client=client))
