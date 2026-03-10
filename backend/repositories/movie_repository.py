from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import Genre, Movie, MovieGenre


class MovieRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_movie_by_title(self, title: str) -> Movie | None:
        normalized_title = title.strip()
        if not normalized_title:
            return None

        return (
            self.db.query(Movie)
            .filter(func.lower(Movie.title) == normalized_title.lower())
            .first()
        )

    def create_movie(self, movie_data: dict) -> Movie:
        movie = Movie(
            kinopoisk_id=movie_data.get("kinopoisk_id"),
            title=movie_data.get("title"),
            short_description=movie_data.get("short_description"),
            description=movie_data.get("description"),
            poster_url=movie_data.get("poster_url"),
            year=movie_data.get("year"),
            rating=movie_data.get("rating"),
            runtime=movie_data.get("runtime"),
            cached_at=movie_data.get("cached_at", datetime.now(timezone.utc)),
        )
        self.db.add(movie)
        self.db.flush()

        self._sync_genres(movie, movie_data.get("genres", []))
        self.db.commit()
        self.db.refresh(movie)
        return movie

    def update_movie(self, movie: Movie, movie_data: dict) -> Movie:
        movie.kinopoisk_id = movie_data.get("kinopoisk_id", movie.kinopoisk_id)
        movie.title = movie_data.get("title", movie.title)
        movie.short_description = movie_data.get("short_description")
        movie.description = movie_data.get("description")
        movie.poster_url = movie_data.get("poster_url")
        movie.year = movie_data.get("year")
        movie.rating = movie_data.get("rating")
        movie.runtime = movie_data.get("runtime")
        movie.cached_at = movie_data.get("cached_at", datetime.now(timezone.utc))

        self._sync_genres(movie, movie_data.get("genres", []))
        self.db.commit()
        self.db.refresh(movie)
        return movie

    def _sync_genres(self, movie: Movie, genres: list[str]) -> None:
        unique_genres = {name.strip() for name in genres if name and name.strip()}
        current_links = (
            self.db.query(MovieGenre)
            .join(Genre, Genre.id == MovieGenre.genre_id)
            .filter(MovieGenre.movie_id == movie.id)
            .all()
        )

        current_genres_by_name = {link.genre.name: link for link in current_links}

        # Удаляем связи с жанрами, которых больше нет в актуальном ответе API.
        for genre_name, link in current_genres_by_name.items():
            if genre_name not in unique_genres:
                self.db.delete(link)

        # Добавляем только недостающие связи.
        for genre_name in unique_genres:
            if genre_name in current_genres_by_name:
                continue

            genre = self.db.query(Genre).filter(Genre.name == genre_name).first()
            if genre is None:
                genre = Genre(name=genre_name)
                self.db.add(genre)
                self.db.flush()

            self.db.add(MovieGenre(movie_id=movie.id, genre_id=genre.id))
