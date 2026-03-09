import httpx

from backend.settings import KINOPOISK_API_KEY


class KinopoiskClient:
    BASE_URL = "https://api.kinopoisk.dev/v1.4"

    def __init__(self, api_key: str | None = None, timeout: float = 10.0) -> None:
        self.api_key = api_key or KINOPOISK_API_KEY
        self.timeout = timeout

    def search_movie(self, title: str) -> dict | None:
        if not self.api_key:
            raise ValueError("KINOPOISK_API_KEY is not configured")

        response = httpx.get(
            f"{self.BASE_URL}/movie/search",
            params={"query": title, "page": 1, "limit": 1},
            headers={"X-API-KEY": self.api_key},
            timeout=self.timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
        payload = response.json()
        docs = payload.get("docs", [])
        if not docs:
            return None
        return docs[0]
