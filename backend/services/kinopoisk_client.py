import logging

import httpx

from backend.settings import KINOPOISK_API_KEY

logger = logging.getLogger(__name__)


class KinopoiskClient:
    BASE_URL = "https://api.kinopoisk.dev/v1.4"

    def __init__(self, api_key: str | None = None, timeout: float = 10.0) -> None:
        self.api_key = api_key or KINOPOISK_API_KEY
        self.timeout = timeout

    async def search_movie(self, title: str) -> dict | None:
        if not self.api_key:
            raise ValueError("KINOPOISK_API_KEY is not configured")

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                f"{self.BASE_URL}/movie/search",
                params={"query": title, "page": 1, "limit": 1},
                headers={"X-API-KEY": self.api_key},
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Kinopoisk response payload must be a JSON object")

            if "docs" not in payload:
                logger.error("Kinopoisk payload missing docs field")
                raise ValueError("Kinopoisk response payload does not contain docs")

            docs = payload["docs"]
            if not isinstance(docs, list):
                logger.error("Kinopoisk payload docs field has invalid type: %s", type(docs).__name__)
                raise ValueError("Kinopoisk response payload field docs must be a list")

            if not docs:
                return None
            if not isinstance(docs[0], dict):
                logger.error("Kinopoisk payload docs[0] has invalid type: %s", type(docs[0]).__name__)
                raise ValueError("Kinopoisk response payload docs items must be JSON objects")
            return docs[0]
