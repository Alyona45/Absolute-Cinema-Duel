from datetime import datetime, timezone

import logging
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models import Genre, Movie, MovieGenre
from backend.schemas.movie import MovieCreate, MovieUpdate

logger = logging.getLogger(__name__)


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

    def get_movie_by_kinopoisk_id(self, kinopoisk_id: int) -> Movie | None:
        return self.db.query(Movie).filter(Movie.kinopoisk_id == kinopoisk_id).first()

    def create_movie(
        self,
        movie_data: MovieCreate,
        genres: list[str] | None = None,
        cached_at: datetime | None = None,
    ) -> Movie:
        movie = Movie(
            kinopoisk_id=movie_data.kinopoisk_id,
            title=movie_data.title,
            short_description=movie_data.short_description,
            description=movie_data.description,
            poster_url=movie_data.poster_url,
            year=movie_data.year,
            rating=movie_data.rating,
            runtime=movie_data.runtime,
            cached_at=cached_at or datetime.now(timezone.utc),
        )
        try:
            self.db.add(movie)
            self.db.flush()

            self._sync_genres(movie, genres or [])
            self.db.commit()
            self.db.refresh(movie)
            return movie
        except IntegrityError:
            self.db.rollback()
            logger.warning(
                "Movie create hit integrity error, retrying via existing row kinopoisk_id=%s",
                movie_data.kinopoisk_id,
                exc_info=True,
            )

            existing_movie = self.get_movie_by_kinopoisk_id(movie_data.kinopoisk_id)
            if existing_movie is None:
                raise

            return self.update_movie(
                existing_movie,
                MovieUpdate(**movie_data.model_dump()),
                genres=genres,
                cached_at=cached_at,
            )
        except SQLAlchemyError:
            self.db.rollback()
            logger.exception("Movie create failed, transaction rolled back")
            raise

    def update_movie(
        self,
        movie: Movie,
        movie_data: MovieUpdate,
        genres: list[str] | None = None,
        cached_at: datetime | None = None,
    ) -> Movie:
        try:
            update_fields = movie_data.model_dump(exclude_unset=True)

            if "kinopoisk_id" in update_fields:
                movie.kinopoisk_id = movie_data.kinopoisk_id
            if "title" in update_fields:
                movie.title = movie_data.title
            if "short_description" in update_fields:
                movie.short_description = movie_data.short_description
            if "description" in update_fields:
                movie.description = movie_data.description
            if "poster_url" in update_fields:
                movie.poster_url = movie_data.poster_url
            if "year" in update_fields:
                movie.year = movie_data.year
            if "rating" in update_fields:
                movie.rating = movie_data.rating
            if "runtime" in update_fields:
                movie.runtime = movie_data.runtime
            movie.cached_at = cached_at or datetime.now(timezone.utc)

            self._sync_genres(movie, genres or [])
            self.db.commit()
            self.db.refresh(movie)
            return movie
        except SQLAlchemyError:
            self.db.rollback()
            logger.exception("Movie update failed, transaction rolled back")
            raise

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
                try:
                    with self.db.begin_nested():
                        genre = Genre(name=genre_name)
                        self.db.add(genre)
                        self.db.flush()
                except IntegrityError:
                    genre = self.db.query(Genre).filter(Genre.name == genre_name).first()
                    if genre is None:
                        raise

            link_exists = (
                self.db.query(MovieGenre)
                .filter(
                    MovieGenre.movie_id == movie.id,
                    MovieGenre.genre_id == genre.id,
                )
                .first()
            )
            if link_exists is None:
                try:
                    with self.db.begin_nested():
                        self.db.add(MovieGenre(movie_id=movie.id, genre_id=genre.id))
                        self.db.flush()
                except IntegrityError:
                    continue
