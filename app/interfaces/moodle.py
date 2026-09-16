import json
import logging
from collections.abc import Iterator
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.bots.explique.utils import casefold_and_collapse_whitespace
from app.config import MoodleConfig, config

logger = logging.getLogger(__name__)

REST_PATH = "/webservice/rest/server.php"


class MoodleError(Exception):
    """A call that did not come back with a usable answer."""


class MoodleUnavailable(MoodleError):
    """No answer from Moodle. Worth retrying."""


class MoodleRefused(MoodleError):
    """Moodle answered, and the call cannot work as-is. Not worth retrying."""


class MoodleUser(BaseModel):
    """A user according to `core_user_get_users_by_field`."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: int


class MoodleCourse(BaseModel):
    """A course a user is enrolled in, according to `core_enrol_get_users_courses`."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: int


class MoodleGroup(BaseModel):
    """A group according to `core_group_get_course_groups` and `core_group_create_groups`."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: int
    name: str


class MoodleModule(BaseModel):
    """One activity, according to `core_course_get_contents`.

    `availability` is the restriction tree, sent as a JSON string and only when the
    activity has one. `url` is missing on modules with nothing to open, like labels.
    `visible` is the teaching team's show/hide toggle.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: int
    modname: str
    name: str | None = None
    url: str | None = None
    availability: str | None = None
    visible: bool = True

    def restriction_group_ids(self) -> set[int]:
        """Every group in this activity's restrict-access rules.

        Empty where it is unrestricted, or where its rules cannot be read.
        """
        if not self.availability:
            return set()

        try:
            return set(_group_ids(json.loads(self.availability)))
        except ValueError:
            logger.warning("Activity cmid=%s has unreadable availability rules; ignoring them", self.id)
            return set()


def _group_ids(condition: Any) -> Iterator[int]:
    """Every group id in a restrict-access tree, whatever the operators between them.

    The tree nests: conditions group under `c`, and a group is itself a condition.
    """
    if not isinstance(condition, dict):
        return

    if condition.get("type") == "group":
        group_id = condition.get("id")
        if isinstance(group_id, int):
            yield group_id

    for child in condition.get("c", []):
        yield from _group_ids(child)


class MoodleSection(BaseModel):
    """A course section, modelled only as the wrapper `course_modules` unpacks."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    modules: tuple[MoodleModule, ...]


Response = TypeVar("Response", bound=BaseModel)


class MoodleClient:
    """The gate exercise's Moodle calls, over its REST web services.

    Resolves a student, checks the course they are enrolled in, puts them in a topic's
    group, and reads the course's activity list to find which quizzes it opens. What the
    reward *is* — who may see it, when it opens — stays a restriction rule
    configured in Moodle itself, so it is not this client's business.
    """

    def __init__(self, config: MoodleConfig):
        self.config = config
        self._http_client: httpx.AsyncClient | None = None

    @property
    def configured(self) -> bool:
        return self.config.configured

    @property
    def http_client(self) -> httpx.AsyncClient:
        """The connection pool, opened on first use and reused for every later call.

        Built lazily here instead of __init__, so importing this module
        doesn't create a pool or tie it to a specific event loop.
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(base_url=self.config.base_url or "", timeout=self.config.timeout)

        return self._http_client

    async def aclose(self) -> None:
        """Close the pool. Called once, on shutdown."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _call(self, function: str, params: dict[str, Any]) -> Any:
        """One REST call, or `MoodleError` — Moodle answers 200 either way."""
        if not self.configured:
            raise MoodleRefused("Moodle is not configured (base_url and token needed)")

        payload = {
            **params,
            "wstoken": self.config.token,
            "wsfunction": function,
            "moodlewsrestformat": "json",
        }
        try:
            response = await self.http_client.post(url=REST_PATH, data=payload)
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError as error:
            # 5xx is a server having a bad minute; 4xx means the URL, or whatever sits
            # in front of it, is wrong — asking again would not change the answer.
            exception_cls = MoodleUnavailable if error.response.is_server_error else MoodleRefused
            raise exception_cls(f"{function} got HTTP {error.response.status_code}") from error
        except (httpx.HTTPError, ValueError) as error:
            # Nothing answered — DNS, TLS, a timeout — or what answered was not JSON,
            # which `.json()` reports as a `ValueError`. Both may be gone by next turn.
            raise MoodleUnavailable(f"{function} could not be called: {error}") from error

        # Moodle sends refusals as a 200 with an exception in the body.
        if isinstance(result, dict) and "exception" in result:
            raise MoodleRefused(f"{function} refused: {result.get('errorcode')} — {result.get('message')}")

        return result

    async def _call_and_validate(self, function: str, params: dict[str, Any], schema: type[Response]) -> list[Response]:
        """`_call`, with the answer validated into `schema`.

        Every web service this client uses answers with a list. A body that does not
        fit counts as a refusal: the same call would come back the same way.
        """
        result = await self._call(function=function, params=params)
        try:
            return [schema.model_validate(obj=item) for item in result]
        except (TypeError, ValidationError) as error:
            raise MoodleRefused(f"{function} answered with a body this client cannot read: {error}") from error

    async def get_user_id_by_email(self, email: str) -> int | None:
        """Moodle's id for `email`, or None if it knows no such user."""
        users = await self._call_and_validate(
            function="core_user_get_users_by_field",
            params={"field": "email", "values[0]": email},
            schema=MoodleUser,
        )
        if not users:
            logger.warning("Could not find user with email %r in Moodle", email)
            return None

        return users[0].id

    async def get_user_course_ids(self, user_id: int) -> set[int]:
        """Every course `user_id` is actively enrolled in, as far as this client can see.

        A course this client cannot view the participants of is dropped from the answer
        rather than refused, so a missing `moodle/course:viewparticipants` reads here as
        an enrolment the student does not have.
        """
        courses = await self._call_and_validate(
            function="core_enrol_get_users_courses",
            params={"userid": user_id, "returnusercount": 0},
            schema=MoodleCourse,
        )
        return {course.id for course in courses}

    async def get_course_modules(self, course_id: int) -> list[MoodleModule]:
        """Every activity in `course_id`, flattened out of Moodle's sections."""
        sections = await self._call_and_validate(
            function="core_course_get_contents",
            params={"courseid": course_id},
            schema=MoodleSection,
        )
        return [module for section in sections for module in section.modules]

    async def get_group_ids_by_name(self, course_id: int) -> dict[str, int]:
        """Every group in `course_id`, keyed by its name normalized for matching."""
        groups = await self._call_and_validate(
            function="core_group_get_course_groups",
            params={"courseid": course_id},
            schema=MoodleGroup,
        )
        group_ids = {}
        for group in groups:
            group_ids.setdefault(casefold_and_collapse_whitespace(text=group.name), group.id)

        return group_ids

    async def get_group_id_by_name(self, course_id: int, group_name: str) -> int | None:
        """The id of `course_id`'s group called `group_name`, or None if it has none."""
        group_ids = await self.get_group_ids_by_name(course_id)
        return group_ids.get(casefold_and_collapse_whitespace(text=group_name))

    async def create_group(self, course_id: int, group_name: str) -> int:
        """Create the group `group_name` in `course_id` and return its id."""
        new_groups = await self._call_and_validate(
            function="core_group_create_groups",
            params={"groups[0][courseid]": course_id, "groups[0][name]": group_name, "groups[0][description]": ""},
            schema=MoodleGroup,
        )
        group_id = new_groups[0].id
        logger.info("Created group %r (id=%s) in course %s", group_name, group_id, course_id)
        return group_id

    async def add_group_member(self, group_id: int, user_id: int) -> None:
        """Add `user_id` to `group_id`, regardless of whether they are already a member."""
        await self._call(
            function="core_group_add_group_members",
            params={"members[0][groupid]": group_id, "members[0][userid]": user_id},
        )
        logger.info("User %s added to group %s", user_id, group_id)


moodle = MoodleClient(config=config.moodle)
