from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.models import Movie
from backend.repositories import MovieRepository
from backend.services.kinopoisk_client import KinopoiskClient


class MovieService:
    CACHE_TTL_DAYS = 30

    def __init__(
        self,
        db: Session,
        kinopoisk_client: KinopoiskClient | None = None,
    ) -> None:
        self.repository = MovieRepository(db)
        self.kinopoisk_client = kinopoisk_client or KinopoiskClient()

    def get_movie_by_title(self, title: str) -> Movie | None:
        movie = self.repository.get_movie_by_title(title)

        if movie and not self._is_cache_expired(movie.cached_at):
            return movie

        api_movie = self.kinopoisk_client.search_movie(title)
        if api_movie is None:
            return movie

        movie_data = self._normalize_api_movie(api_movie)
        movie_data["cached_at"] = datetime.utcnow()

        if movie:
            return self.repository.update_movie(movie, movie_data)
        return self.repository.create_movie(movie_data)

    def _is_cache_expired(self, cached_at: datetime) -> bool:
        return cached_at + timedelta(days=self.CACHE_TTL_DAYS) <= datetime.utcnow()

    def _normalize_api_movie(self, api_movie: dict) -> dict:
        poster = api_movie.get("poster") or {}
        rating = api_movie.get("rating") or {}

        return {
            "kinopoisk_id": api_movie.get("id"),
            "title": api_movie.get("name") or api_movie.get("alternativeName"),
            "short_description": api_movie.get("shortDescription"),
            "description": api_movie.get("description"),
            "poster_url": poster.get("url") or poster.get("previewUrl"),
            "year": api_movie.get("year"),
            "rating": rating.get("kp"),
            "runtime": api_movie.get("movieLength"),
            "genres": [item.get("name") for item in api_movie.get("genres", []) if item.get("name")],
        }
