import logging

import httpx

from backend.settings import KINOPOISK_API_KEY

logger = logging.getLogger(__name__)


class KinopoiskClient:
    # This host is where kinopoisk.dev redirects API traffic.
    BASE_URL = "https://api.poiskkino.dev/v1.4"
    # BASE_URL = "https://api.kinopoisk.dev/v1.4"

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

    async def search_popular_russian_movies(self, limit: int = 20) -> list[dict]:
        """Search for popular Russian movies by predefined queries."""
        if not self.api_key:
            raise ValueError("KINOPOISK_API_KEY is not configured")

        # Popular Russian movie titles and search terms
        search_queries = [
            "Тот самый Мюнхгаузен",
            "Красивая жизнь",
            "Плывущие облака",
            "Боец",
            "Легенда № 17",
            "О чём говорят мужчины",
            "Сулусулу",
            "Мастер и Маргарита",
            "Война и мир",
            "Броненосец Потёмкин",
        ]

        collected = {}
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            for query in search_queries:
                if len(collected) >= limit:
                    break

                try:
                    response = await client.get(
                        f"{self.BASE_URL}/movie/search",
                        params={"query": query, "page": 1, "limit": 5},
                        headers={"X-API-KEY": self.api_key},
                    )
                    response.raise_for_status()
                    payload = response.json()
                    docs = self._extract_docs(payload)

                    for doc in docs:
                        if len(collected) >= limit:
                            break
                        if isinstance(doc, dict) and "id" in doc:
                            kp_id = doc["id"]
                            if kp_id not in collected:
                                collected[kp_id] = doc
                except Exception as e:
                    logger.warning(f"Failed to search for '{query}': {e}")
                    continue

        return list(collected.values())[:limit]

    def search_popular_russian_movies_sync(self, limit: int = 20) -> list[dict]:
        """Synchronous search for popular Russian movies."""
        if not self.api_key:
            raise ValueError("KINOPOISK_API_KEY is not configured")

        # Popular Russian movie titles and search terms
        search_queries = [
            "Тот самый Мюнхгаузен",
            "Красивая жизнь",
            "Плывущие облака",
            "Боец",
            "Легенда № 17",
            "О чём говорят мужчины",
            "Сулусулу",
            "Мастер и Маргарита",
            "Война и мир",
            "Броненосец Потёмкин",
        ]

        collected = {}
        with httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            for query in search_queries:
                if len(collected) >= limit:
                    break

                try:
                    response = client.get(
                        f"{self.BASE_URL}/movie/search",
                        params={"query": query, "page": 1, "limit": 5},
                        headers={"X-API-KEY": self.api_key},
                    )
                    response.raise_for_status()
                    payload = response.json()
                    docs = self._extract_docs(payload)

                    for doc in docs:
                        if len(collected) >= limit:
                            break
                        if isinstance(doc, dict) and "id" in doc:
                            kp_id = doc["id"]
                            if kp_id not in collected:
                                collected[kp_id] = doc
                except Exception as e:
                    logger.warning(f"Failed to search for '{query}': {e}")
                    continue

        return list(collected.values())[:limit]

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
