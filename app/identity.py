import logging

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# Open WebUI forwards these headers when ENABLE_FORWARD_USER_INFO_HEADERS is enabled.
# They identify the requesting user, since the OpenAI-compatible request body
# contains only the model name and messages.
ID_HEADER = "X-OpenWebUI-User-Id"
EMAIL_HEADER = "X-OpenWebUI-User-Email"


class Requester(BaseModel):
    """The person a request claims to be from, as the chat frontend reports them.

    Unverified: the frontend forwards them as plain headers, so a request that
    reaches this app by another route can claim to be anyone.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    email: str | None = Field(default=None, exclude=True, repr=False)


def requester_from_headers(request: Request) -> Requester | None:
    """Who sent `request`, or None when the frontend forwarded no identity."""
    requester_id = request.headers.get(ID_HEADER)
    if not requester_id:
        logger.debug("Request carried no %s header", ID_HEADER)
        return None

    return Requester(id=requester_id, email=request.headers.get(EMAIL_HEADER))
