import asyncio
import logging
import time

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.config import config
from app.logging_config import truncate

logger = logging.getLogger(__name__)


class RAGChunk(BaseModel):
    """One chunk as the RAG index returns it."""

    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    type: str | None = None
    subtype: str | None = None
    title: str | None = None
    original_link: str | None = None
    page: list[int] | None = None
    position: str | None = None
    content: str | None = None
    content_en: str | None = Field(default=None, alias="content.en")
    content_fr: str | None = Field(default=None, alias="content.fr")
    week: int | None = None
    number: int | None = None
    associated_video_lectures: list["RAGChunk"] | None = None

    @property
    def chunk_type(self) -> str | None:
        """`type: subtype` — never the literal string "None" when either is missing."""
        if self.type is None:
            return None
        return f"{self.type}: {self.subtype}" if self.subtype is not None else self.type

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True, by_alias=True)


class RAGResult(BaseModel):
    """The RAG endpoint's response: a batch of chunks, each validated on its
    own so one malformed chunk is dropped and logged rather than failing the
    whole retrieval."""

    model_config = ConfigDict(frozen=True)

    chunks: list[RAGChunk]

    @field_validator("chunks", mode="before")
    @classmethod
    def validate_chunks(cls, raw: list[dict]) -> list[RAGChunk]:
        chunks = []
        for item in raw:
            try:
                chunks.append(RAGChunk.model_validate(item))
            except ValidationError as error:
                logger.warning(f"Dropping RAG result that failed validation: {truncate(error)}")
        return chunks

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True, by_alias=True)

    def __add__(self, other: "RAGResult") -> "RAGResult":
        return RAGResult(chunks=self.chunks + other.chunks)


EMPTY_RAG_RESULT = RAGResult(chunks=[])


class GraphAIClient:
    def __init__(self):
        self.url = f"{config.graphai.host}:{config.graphai.port}"
        self.username = config.graphai.username
        self.password = config.graphai.password

        self.bearer_token = None

    async def authenticate(self):
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "scope": "",
            "client_id": "",
            "client_secret": "",
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.url}/token", headers=headers, data=data)
                result = resp.json()

                self.bearer_token = result.get("access_token")
                if not self.bearer_token:
                    logger.error(f"Unexpected authentication response: {truncate(result)}")

        except httpx.TimeoutException:
            logger.warning("Request to authenticate timed out, subsequent requests will more likely fail.")

    async def call_async_endpoint(self, endpoint, payload, timeout=10, verbose=False):
        # Make sure we are authenticated
        await self.authenticate()

        headers = {"Authorization": f"Bearer {self.bearer_token}"}

        async with httpx.AsyncClient(timeout=timeout) as client:
            # Make first request, which will return a task_id
            resp = await client.post(f"{self.url}{endpoint}", headers=headers, json=payload)
            response = resp.json()

            if verbose:
                logger.debug(response)

            task_id = response["task_id"]

            # Poll for result until timeout is reached
            limit_time = time.time() + timeout

            while True:
                resp = await client.get(f"{self.url}{endpoint}/status/{task_id}", headers=headers)
                response = resp.json()

                if verbose:
                    logger.debug(response)

                # If result is available, return it
                if response.get("task_result") is not None:
                    return response["task_result"]

                # If status is FAILURE, return immediately
                if response.get("task_status") == "FAILURE":
                    logger.error(f"Task failed: {truncate(response)}")
                    return None

                # Stop if timeout is reached
                if time.time() > limit_time:
                    logger.warning(f"Timeout reached for payload {truncate(payload)}")
                    break

                # Wait before next iteration
                await asyncio.sleep(1)

        return None

    async def call_sync_endpoint(self, endpoint, payload, timeout=30, verbose=False):
        # Make sure we are authenticated
        await self.authenticate()

        headers = {"Authorization": f"Bearer {self.bearer_token}"}

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{self.url}{endpoint}", headers=headers, json=payload)
                response = resp.json()

                if verbose:
                    logger.debug(response)

                return response
        except httpx.TimeoutException:
            logger.warning(f"Request to {endpoint} timed out after {timeout} seconds, returning None")
            return None

    async def rag_retrieve(
        self, index: str, texts: list[str], limit: int = 10, filters: BaseModel | None = None
    ) -> RAGResult:
        # Clean texts
        texts = [text.strip() for text in texts if text.strip()]

        # Join texts into one string
        texts = "    ".join(texts)

        # Prepare payload
        payload = {
            "index": index,
            "text": texts,
            "limit": limit,
        }

        filters_dict = filters.model_dump(exclude_none=True) if filters else {}
        if filters_dict:
            payload["filters"] = filters_dict

        # Send request and return empty if it fails
        try:
            response = await self.call_sync_endpoint(endpoint="/rag/retrieve", payload=payload)
        except Exception as error:
            logger.exception(f"Error retrieving document chunks: {error}")
            return EMPTY_RAG_RESULT

        # Return empty if there is no response (a timed-out request answers None)
        # or it is not marked as successful
        if not response or not response.get("successful"):
            logger.warning(f"Unsuccessful retrieval of chunks: {truncate(response and response.get('result', []))}")
            return EMPTY_RAG_RESULT

        return RAGResult(chunks=response.get("result", []))


# Shared singleton — re-authenticates before each request so it never goes stale
graphai = GraphAIClient()
