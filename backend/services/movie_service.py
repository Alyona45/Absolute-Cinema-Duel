from datetime import datetime, timedelta, timezone

import httpx
import logging
from sqlalchemy.orm import Session

from backend.models import Movie
from backend.repositories import MovieRepository
from backend.schemas.movie import MovieCreate, MovieUpdate
from backend.services.kinopoisk_client import KinopoiskClient

logger = logging.getLogger(__name__)


class MovieService:
    CACHE_TTL_DAYS = 30

    def __init__(
        self,
        db: Session,
        kinopoisk_client: KinopoiskClient | None = None,
    ) -> None:
        self.repository = MovieRepository(db)
        self.kinopoisk_client = kinopoisk_client or KinopoiskClient()

    async def get_movie_by_title(self, title: str) -> Movie | None:
        if not title.strip():
            logger.info("Skipping movie lookup because title is empty")
            return None

        movie = self.repository.get_movie_by_title(title)

        if movie and not self._is_cache_expired(movie.cached_at):
            return movie

        try:
            api_movie = await self.kinopoisk_client.search_movie(title)
        except (httpx.HTTPError, httpx.TimeoutException):
            if movie is not None:
                logger.warning("Kinopoisk request failed, returning stale cache for title=%r", title, exc_info=True)
                return movie
            raise

        if api_movie is None:
            return movie

        try:
            movie_data = self._normalize_api_movie(api_movie)
        except ValueError:
            if movie is not None:
                logger.warning("Invalid Kinopoisk payload, returning stale cache for title=%r", title, exc_info=True)
                return movie
            raise

        cached_at = datetime.now(timezone.utc)
        genres = movie_data.pop("genres", [])
        current_movie = self.repository.get_movie_by_kinopoisk_id(movie_data["kinopoisk_id"])

        if current_movie:
            return self.repository.update_movie(
                current_movie,
                MovieUpdate(**movie_data),
                genres=genres,
                cached_at=cached_at,
            )
        if movie:
            return self.repository.update_movie(
                movie,
                MovieUpdate(**movie_data),
                genres=genres,
                cached_at=cached_at,
            )
        return self.repository.create_movie(
            MovieCreate(**movie_data),
            genres=genres,
            cached_at=cached_at,
        )

    def _is_cache_expired(self, cached_at: datetime) -> bool:
        normalized_cached_at = cached_at
        if normalized_cached_at.tzinfo is None or normalized_cached_at.utcoffset() is None:
            normalized_cached_at = normalized_cached_at.replace(tzinfo=timezone.utc)

        return normalized_cached_at + timedelta(days=self.CACHE_TTL_DAYS) <= datetime.now(timezone.utc)

    def _normalize_api_movie(self, api_movie: dict) -> dict:
        kinopoisk_id = api_movie.get("id")
        if kinopoisk_id is None:
            logger.error("Kinopoisk payload missing required movie id: %r", api_movie)
            raise ValueError("Kinopoisk response does not contain required movie id")

        title = api_movie.get("name") or api_movie.get("alternativeName")
        if title is None:
            logger.error("Kinopoisk payload missing required movie title: %r", api_movie)
            raise ValueError("Kinopoisk response does not contain required movie title")

        movie_data = {
            "kinopoisk_id": kinopoisk_id,
            "title": title,
        }

        if "shortDescription" in api_movie:
            movie_data["short_description"] = api_movie.get("shortDescription")
        if "description" in api_movie:
            movie_data["description"] = api_movie.get("description")
        if "year" in api_movie:
            movie_data["year"] = api_movie.get("year")
        if "movieLength" in api_movie:
            movie_data["runtime"] = api_movie.get("movieLength")
        if "genres" in api_movie:
            movie_data["genres"] = [
                item.get("name") for item in api_movie.get("genres", []) if item.get("name")
            ]

        if "poster" in api_movie:
            poster = api_movie.get("poster") or {}
            movie_data["poster_url"] = poster.get("url") or poster.get("previewUrl")

        if "rating" in api_movie:
            rating = api_movie.get("rating") or {}
            movie_data["rating"] = rating.get("kp")

        return movie_data
