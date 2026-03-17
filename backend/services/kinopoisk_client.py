import logging

import httpx

from backend.settings import KINOPOISK_API_KEY

logger = logging.getLogger(__name__)


class KinopoiskClient:
    BASE_URL = "https://api.kinopoisk.dev/v1.4"

    def __init__(self, api_key: str | None = None, timeout: float = 10.0) -> None:
        self.api_key = api_key or KINOPOISK_API_KEY
        self.timeout = timeout

    async def search_movies(self, title: str, limit: int = 5) -> list[dict]:
        if not self.api_key:
            raise ValueError("KINOPOISK_API_KEY is not configured")

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                f"{self.BASE_URL}/movie/search",
                params={"query": title, "page": 1, "limit": limit},
                headers={"X-API-KEY": self.api_key},
            )
            response.raise_for_status()
            payload = response.json()

        return self._extract_docs(payload)

    async def get_movie_by_id(self, kinopoisk_id: int) -> dict | None:
        if not self.api_key:
            raise ValueError("KINOPOISK_API_KEY is not configured")

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                f"{self.BASE_URL}/movie/{kinopoisk_id}",
                headers={"X-API-KEY": self.api_key},
            )
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, dict):
            raise ValueError("Kinopoisk response payload must be a JSON object")

        return payload

    def _extract_docs(self, payload: object) -> list[dict]:
        if not isinstance(payload, dict):
            raise ValueError("Kinopoisk response payload must be a JSON object")

        if "docs" not in payload:
            logger.error("Kinopoisk payload missing docs field")
            raise ValueError("Kinopoisk response payload does not contain docs")

        docs = payload["docs"]
        if not isinstance(docs, list):
            logger.error("Kinopoisk payload docs field has invalid type: %s", type(docs).__name__)
            raise ValueError("Kinopoisk response payload field docs must be a list")

        invalid_items = [item for item in docs if not isinstance(item, dict)]
        if invalid_items:
            logger.error("Kinopoisk payload docs contains non-object items")
            raise ValueError("Kinopoisk response payload docs items must be JSON objects")

        return docs
