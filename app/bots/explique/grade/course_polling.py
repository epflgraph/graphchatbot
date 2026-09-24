import asyncio
import logging
import re
from dataclasses import dataclass
from operator import attrgetter

from app.bots.base import Bot
from app.bots.explique.grade.coverage_record import ASSESSMENT_ACTIVITY_TYPES, TOPIC_GROUP_NAME
from app.bots.explique.grade.explique_bot import ExpliqueGradeBot
from app.bots.explique.grade.topics import Topics
from app.bots.explique.utils import casefold_and_collapse_whitespace
from app.interfaces.moodle import MoodleClient, MoodleError, MoodleModule, moodle

logger = logging.getLogger(__name__)

# What the professor writes in an activity's title to say which topic it belongs to, case ignored.
TOPIC_TAG = re.compile(r"\[TOPIC:([^\]]*)\]", re.IGNORECASE)


def topics_in_activity_title(title: str) -> tuple[str, ...]:
    """The topics `title` is tagged with, in the order written, each one kept once."""
    names = []
    lookup = set()

    for name in TOPIC_TAG.findall(title):
        normalized = casefold_and_collapse_whitespace(name)
        if normalized and normalized not in lookup:
            lookup.add(normalized)
            names.append(name.strip())

    return tuple(names)


@dataclass(frozen=True)
class PollingReport:
    """What one polling pass over a course found: a fully set-up course is two empty tuples."""

    # Ready for a professor to restrict a quiz to.
    created_groups: tuple[str, ...] = ()
    # The topic's group exists but no quiz restricts to it.
    unrestricted_topics: tuple[str, ...] = ()


@dataclass
class PollingState:
    """What polling one course remembers between passes."""

    # What was last logged, so a problem that stands for days is not repeated every pass.
    reported_unrestricted_topics: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaggedTopic:
    """A topic tagged on a course's activities, and every activity carrying it."""

    name: str
    activities: tuple[MoodleModule, ...]

    @property
    def visible(self) -> bool:
        """Whether a student can see any of the activities carrying this topic."""
        return any(activity.visible for activity in self.activities)


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
            key = casefold_and_collapse_whitespace(topic)
            topic_names.setdefault(key, topic)
            activities.setdefault(key, []).append(module)

    return tuple(TaggedTopic(name=name, activities=tuple(activities[key])) for key, name in topic_names.items())


async def poll_course(bot: ExpliqueGradeBot, *, client: MoodleClient = moodle) -> PollingReport:
    """One pass: a group for every tagged quiz, and the setup only the teacher can finish."""
    # The whole course, narrowed to the assessments whose title carries a `[TOPIC: ...]` tag.
    tagged_topics = _tagged_topics(await client.get_course_modules(bot.course_id))
    # Published to the bot, and only once the read above succeeded: a failed pass raises
    # before here, so an outage leaves the last good menu standing rather than nuking it.
    bot.topics = Topics.from_names(topic.name for topic in tagged_topics if topic.visible)

    created = []
    unrestricted = []

    # Every group the course has, in one call. Read every pass so a deleted group is recreated and reported.
    group_ids_by_name = await client.get_group_ids_by_name(bot.course_id)

    for topic in tagged_topics:
        # Named the way a finished session looks it up, so it finds this group
        # rather than a second one spelled differently.
        group_name = TOPIC_GROUP_NAME.format(topic=topic.name)
        group_id = group_ids_by_name.get(casefold_and_collapse_whitespace(group_name))
        if group_id is None:
            # Nobody has made it: the group is explique's own, so make it here.
            try:
                group_id = await client.create_group(bot.course_id, group_name)
            except MoodleError:
                # One refused topic must not stop the others.
                logger.warning(
                    "Could not create group for topic %r in course %s", topic.name, bot.course_id, exc_info=True
                )
                continue
            created.append(topic.name)

        # The professor's own step, since no Moodle API can set it: they point the quiz's
        # "Restrict access" at this group, and this is where a later pass reads that they did.
        if not any(group_id in activity.restriction_group_ids() for activity in topic.activities):
            unrestricted.append(topic.name)

    return PollingReport(created_groups=tuple(created), unrestricted_topics=tuple(unrestricted))


def _log_report(bot: ExpliqueGradeBot, report: PollingReport, state: PollingState) -> None:
    """Log what one polling pass found."""
    for topic in report.created_groups:
        logger.info("Created group for topic %r in course %s (%s)", topic, bot.course_id, bot.name)

    if report.unrestricted_topics != state.reported_unrestricted_topics:
        if report.unrestricted_topics:
            logger.info(
                "Course %s has %s topic(s) whose quiz is not restricted to their group yet: %s",
                bot.course_id,
                len(report.unrestricted_topics),
                ", ".join(report.unrestricted_topics),
            )
        else:
            logger.info("Course %s has every tagged quiz restricted", bot.course_id)
        state.reported_unrestricted_topics = report.unrestricted_topics


async def _poll_courses(
    bots: list[ExpliqueGradeBot], interval_seconds: float, *, client: MoodleClient = moodle
) -> None:
    """Poll every course forever. One course's failure never stops the others, or the loop."""
    states = {bot.name: PollingState() for bot in bots}
    logger.info("Polling %s course(s) for tagged quizzes every %ss", len(bots), interval_seconds)

    while True:
        for bot in bots:
            state = states[bot.name]
            try:
                report = await poll_course(bot, client=client)
            except MoodleError:
                logger.warning("Moodle failed while polling course %s (%s)", bot.course_id, bot.name, exc_info=True)
            except Exception:
                logger.exception("Polling course %s (%s) failed", bot.course_id, bot.name)
            else:
                _log_report(bot, report, state)

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
        logger.warning(
            "Moodle is not configured, so %s graded bot(s) will offer no topics: %s",
            len(grade_bots),
            ", ".join(bot.name for bot in grade_bots),
        )
        return None

    return asyncio.create_task(_poll_courses(grade_bots, interval_seconds, client=client))
