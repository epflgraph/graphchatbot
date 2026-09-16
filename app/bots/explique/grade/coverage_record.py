import asyncio
import logging
from collections.abc import Callable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.bots.explique.grade.topics import Topic
from app.identity import Requester
from app.interfaces.moodle import MoodleClient, MoodleError, MoodleModule, MoodleRefused, MoodleUnavailable, moodle

logger = logging.getLogger(__name__)

# Told the number of the retry about to be made.
OnRetry = Callable[[int], None]

# The explique topic group; its name is the only key to finding it again.
TOPIC_GROUP_NAME = "Explique: {topic}"

# Which Moodle activity types may stand behind a topic's group.
ASSESSMENT_ACTIVITY_TYPES = ("quiz",)


class CoverageOutcome(StrEnum):
    """How an attempt to record a covered topic ended, and so what the student may be told."""

    RECORDED = "recorded"
    # Recorded, but no assessment to link to.
    RECORDED_NO_LINK = "recorded_no_link"
    # No account to record against: no identity, or Moodle does not know it.
    UNIDENTIFIED = "unidentified"
    # No Moodle to record against. Says nothing about the student.
    NOT_CONFIGURED = "not_configured"
    # Moodle answered, and said no. A retry would be refused the same way.
    REFUSED = "refused"
    # No answer from Moodle, and retrying changed nothing.
    UNAVAILABLE = "unavailable"


class CoverageResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: CoverageOutcome
    assessment_urls: tuple[str, ...] = ()

    @property
    def recorded(self) -> bool:
        return self.outcome in (CoverageOutcome.RECORDED, CoverageOutcome.RECORDED_NO_LINK)

    @property
    def failed(self) -> bool:
        return self.outcome in (CoverageOutcome.UNIDENTIFIED, CoverageOutcome.REFUSED, CoverageOutcome.UNAVAILABLE)


class CoverageRecorder:
    """Records that a student covered a topic, and reports what that opens.

    Judges nothing: `topic_covered` decides that, and this is only reached once it has.
    The record is a membership of the topic's group — created on demand, since the group
    is explique's own — and what it opens is whatever graded activity the teaching team
    restricted to that group.

    Built once per request from the pair that scopes every call: which course, and
    which student.
    """

    # How long a request may spend on Moodle before giving up. `MoodleConfig.timeout`
    # bounds one call; this bounds the sequence, so a student never waits out one call's
    # timeout after another.
    MOODLE_REQUEST_TIMEOUT_SECONDS = 20.0

    # Coverage recording retry configuration (for unresponsive Moodle).
    NUM_RETRIES = 3
    RETRY_INTERVAL_SECONDS = 3.0
    RETRY_MAX_SECONDS = 30.0

    def __init__(self, course_id: int, requester: Requester | None, *, client: MoodleClient = moodle):
        self.course_id = course_id
        self.requester = requester
        self.client = client

    @property
    def student_email(self) -> str | None:
        return self.requester.email if self.requester else None

    @property
    def requester_id(self) -> str | None:
        return self.requester.id if self.requester else None

    async def is_student_enrolled(self) -> bool | None:
        """Whether this student is enrolled in this course.

        False says something about the student: no email, no account, or not on this course.
        None says something about us: no Moodle to ask, or no answer from it."""
        if not self.client.configured:
            logger.debug("Nothing to ask: Moodle is not configured")
            return None

        if self.student_email is None:
            logger.warning("Request carried no email; requester_id=%r", self.requester_id)
            return False

        try:
            async with asyncio.timeout(self.MOODLE_REQUEST_TIMEOUT_SECONDS):
                user_id = await self.client.get_user_id_by_email(self.student_email)
                if user_id is None:
                    return False

                is_enrolled = self.course_id in await self.client.get_user_course_ids(user_id)
        except (MoodleError, TimeoutError):
            logger.warning(
                "Could not check whether %r is enrolled in course %s",
                self.student_email,
                self.course_id,
                exc_info=True,
            )
            return None

        if not is_enrolled:
            logger.warning("%r is not enrolled in course %s", self.student_email, self.course_id)

        return is_enrolled

    async def record(self, topic: Topic, *, on_retry: OnRetry | None = None) -> CoverageResult:
        """Record that this student covered `topic`, and retry if Moodle gives no answer."""
        try:
            async with asyncio.timeout(self.RETRY_MAX_SECONDS):
                for attempt in range(self.NUM_RETRIES + 1):
                    try:
                        return await self._attempt_record(topic)
                    except MoodleUnavailable as error:
                        logger.warning(
                            "Recording %r got no answer on attempt %s of %s: %s",
                            topic.name,
                            attempt + 1,
                            self.NUM_RETRIES + 1,
                            error,
                        )

                    if attempt < self.NUM_RETRIES:
                        if on_retry:
                            on_retry(attempt + 1)
                        await asyncio.sleep(self.RETRY_INTERVAL_SECONDS)
        except TimeoutError:
            logger.warning("Recording %r exceeded the %ss limit", topic.name, self.RETRY_MAX_SECONDS)

        logger.error("Could not record %r for %r; nothing was written", topic.name, self.requester_id)
        return CoverageResult(outcome=CoverageOutcome.UNAVAILABLE)

    async def _attempt_record(self, topic: Topic) -> CoverageResult:
        """One try, bounded: a settled outcome, or `MoodleUnavailable` when nothing answered."""
        try:
            async with asyncio.timeout(self.MOODLE_REQUEST_TIMEOUT_SECONDS):
                return await self._record(topic)
        except TimeoutError as error:
            raise MoodleUnavailable(
                f"Recording {topic.name!r} ran past the {self.MOODLE_REQUEST_TIMEOUT_SECONDS}s Moodle timeout"
            ) from error
        except MoodleRefused:
            logger.critical(
                "Moodle refused to record %r for %r in course %s",
                topic.name,
                self.requester_id,
                self.course_id,
                exc_info=True,
            )
            return CoverageResult(outcome=CoverageOutcome.REFUSED)

    async def _record(self, topic: Topic) -> CoverageResult:
        """The Moodle side of `record`: add the student to the topic's group, and find the activity restricted to it."""
        if not self.client.configured:
            logger.warning("No Moodle to record against; %r goes unrecorded for %r", topic.name, self.requester_id)
            return CoverageResult(outcome=CoverageOutcome.NOT_CONFIGURED)

        if self.student_email is None:
            logger.warning("Request carried no email; %r goes unrecorded by %r", topic.name, self.requester_id)
            return CoverageResult(outcome=CoverageOutcome.UNIDENTIFIED)

        user_id = await self.client.get_user_id_by_email(self.student_email)
        if user_id is None:
            return CoverageResult(outcome=CoverageOutcome.UNIDENTIFIED)

        group_id = await self._get_or_create_group(topic)

        _, modules = await asyncio.gather(
            self.client.add_group_member(group_id, user_id),
            self.client.get_course_modules(self.course_id),
        )

        assessment_urls = self._get_assessment_urls(group_id, modules)
        if not assessment_urls:
            return CoverageResult(outcome=CoverageOutcome.RECORDED_NO_LINK)

        return CoverageResult(outcome=CoverageOutcome.RECORDED, assessment_urls=assessment_urls)

    async def _get_or_create_group(self, topic: Topic) -> int:
        """The id of the topic's group, created on demand if this is the first student to cover it."""
        name = TOPIC_GROUP_NAME.format(topic=topic.name)
        return await self.client.get_group_id_by_name(self.course_id, name) or await self.client.create_group(
            self.course_id, name
        )

    def _get_assessment_urls(self, group_id: int, modules: list[MoodleModule]) -> tuple[str, ...]:
        """Every assessment restricted to `group_id`, read from Moodle's own rules.

        Not matched by name, so a renamed or re-numbered assessment still resolves, and an
        activity restricted to something that is not an explique group is never picked up.
        A hidden one is skipped.
        """
        assessment_urls = tuple(
            module.url
            for module in modules
            if module.modname in ASSESSMENT_ACTIVITY_TYPES
            and module.url
            and module.visible
            and group_id in module.restriction_group_ids()
        )

        if not assessment_urls:
            logger.warning("No assessments found for group %s", group_id)

        return assessment_urls
