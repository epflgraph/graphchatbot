import logging
import time

import aiohttp
import asyncio

from app.config import config

logger = logging.getLogger(__name__)


class GraphAIClient:

    def __init__(self):
        self.url = f"{config['graphai']['host']}:{config['graphai']['port']}"
        self.username = config['graphai']['username']
        self.password = config['graphai']['password']

        self.bearer_token = None

    async def authenticate(self):
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = {
            'grant_type': 'password',
            'username': self.username,
            'password': self.password,
            'scope': '',
            'client_id': '',
            'client_secret': '',
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                        f"{self.url}/token",
                        headers=headers,
                        data=data
                ) as resp:
                    result = await resp.json()

                    try:
                        self.bearer_token = result["access_token"]
                    except KeyError:
                        logger.error(f"Unexpected authentication response: {result}")

            except asyncio.TimeoutError:
                logger.warning("Request to authenticate timed out, subsequent requests will more likely fail.")

    async def call_async_endpoint(self, endpoint, payload, timeout=10, verbose=False):
        # Make sure we are authenticated
        await self.authenticate()

        headers = {'Authorization': f'Bearer {self.bearer_token}'}

        async with aiohttp.ClientSession() as session:
            # Make first request, which will return a task_id
            async with session.post(f"{self.url}{endpoint}", headers=headers, json=payload) as resp:
                response = await resp.json()

            if verbose:
                logger.debug(response)

            task_id = response["task_id"]

            # Poll for result until timeout is reached
            limit_time = time.time() + timeout

            while True:
                async with session.get(f"{self.url}{endpoint}/status/{task_id}", headers=headers) as resp:
                    response = await resp.json()

                if verbose:
                    logger.debug(response)

                # If result is available, return it
                if response.get("task_result") is not None:
                    return response["task_result"]

                # If status is FAILURE, return immediately
                if response.get("task_status") == "FAILURE":
                    logger.error(f"Task failed: {response}")
                    return None

                # Stop if timeout is reached
                if time.time() > limit_time:
                    logger.warning(f"Timeout reached for payload {payload}")
                    break

                # Wait before next iteration
                await asyncio.sleep(1)

        return None

    async def call_sync_endpoint(self, endpoint, payload, timeout=30, verbose=False):
        # Make sure we are authenticated
        await self.authenticate()

        headers = {'Authorization': f'Bearer {self.bearer_token}'}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                        f"{self.url}{endpoint}",
                        headers=headers,
                        json=payload,
                        timeout=timeout
                ) as resp:
                    response = await resp.json()

                    if verbose:
                        logger.debug(response)

                    return response
            except asyncio.TimeoutError:
                logger.warning(f"Request to {endpoint} timed out after {timeout} seconds, returning None")
                return None

    async def rag_retrieve(self, index: str, texts: list[str], limit: int = 10, filters: dict = None):
        # Clean texts
        texts = [text.strip() for text in texts if text.strip()]

        # Join texts into one string
        texts = '    '.join(texts)

        # Prepare payload
        payload = {
            'index': index,
            'text': texts,
            'limit': limit,
        }

        if filters:
            payload['filters'] = filters

        # Send request and return empty if it fails
        try:
            response = await self.call_sync_endpoint(endpoint='/rag/retrieve', payload=payload)
        except Exception as e:
            logger.exception(f"Error retrieving document chunks: {e}")
            return []

        # Return empty if response is not marked as successful
        if not response.get('successful'):
            logger.warning(f"Unsuccessful retrieval of chunks: {response.get('result', [])}")
            return []

        return response.get('result', [])

    def sequential_rag_retrieve(self, index: str, texts: list[str], limit: int = 10, filters: dict = None):
        # Clean texts
        texts = [text.strip() for text in texts if text.strip()]

        # Default to empty string if no texts
        if not texts:
            texts = ['']

        results = {}
        for text in texts:
            # Prepare payload
            payload = {
                'index': index,
                'text': text,
                'limit': limit,
            }

            if filters:
                payload['filters'] = filters

            # Send request and return empty if it fails
            try:
                response = self.call_sync_endpoint(endpoint='/rag/retrieve', payload=payload)
            except Exception as e:
                logger.exception(f"Error retrieving document chunks: {e}")
                continue

            # Return empty if response is not marked as successful
            if not response.get('successful'):
                logger.warning(f"Unsuccessful retrieval of chunks: {response.get('result', [])}")
                continue

            # Store the results to aggregate them later
            i = 0
            for result in response.get('result', []):
                # Score increment is 1 (existence) plus a bonus between 0 and 1 (position)
                score_increment = 2 - i / (limit + 1)
                i += 1

                result_id = result.get('id')
                if not result_id:
                    continue

                if result_id in results:
                    results[result_id]['.score'] += score_increment
                else:
                    results[result_id] = result
                    result['.score'] = score_increment

        # Sort the results in a list by descending score (which is an integer between 1 and n_keywords)
        results = sorted(results.values(), key=lambda result: result['.score'], reverse=True)

        # Keep no more than limit results
        results = results[:limit]

        return results
