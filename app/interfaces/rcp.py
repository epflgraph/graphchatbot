import httpx
from openai import DefaultAsyncHttpxClient

from app.config import config

# Shared by every model client, so calls over the key's limit wait their turn instead of getting a 429.
rcp_http_client = DefaultAsyncHttpxClient(limits=httpx.Limits(max_connections=config.rcp.max_parallel_requests))
