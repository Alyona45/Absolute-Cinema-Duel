from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MovieCreate(BaseModel):
    """Schema для создания/кеширования фильма из данных внешнего API."""

    kinopoisk_id: int
    title: str
    short_description: str | None = None
    description: str | None = None
    poster_url: str | None = None
    year: int | None = None
    runtime: int | None = None
    rating: float | None = None


class MovieResponse(BaseModel):
    """Schema ответа с данными фильма."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    kinopoisk_id: int
    title: str
    short_description: str | None = None
    description: str | None = None
    poster_url: str | None = None
    year: int | None = None
    runtime: int | None = None
    rating: float | None = None
    cached_at: datetime


class MovieUpdate(BaseModel):
    """Schema для обновления кеша фильма. Все поля опциональны."""

    title: str | None = None
    short_description: str | None = None
    description: str | None = None
    poster_url: str | None = None
    year: int | None = None
    runtime: int | None = None
    rating: float | None = None


class GenreResponse(BaseModel):
    """Schema ответа с данными жанра."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
