from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MovieCreate(BaseModel):
    """Schema для создания/кеширования фильма из данных внешнего API."""

    kinopoisk_id: int
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    poster_url: str | None = None
    year: int | None = Field(default=None, ge=1888, le=2100)
    runtime: int | None = Field(default=None, gt=0)
    rating: float | None = Field(default=None, ge=0.0, le=10.0)


class MovieResponse(BaseModel):
    """Schema ответа с данными фильма."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    kinopoisk_id: int
    title: str
    description: str | None = None
    poster_url: str | None = None
    year: int | None = None
    runtime: int | None = None
    rating: float | None = None
    cached_at: datetime


class MovieUpdate(BaseModel):
    """Schema для обновления кеша фильма. Все поля опциональны."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    poster_url: str | None = None
    year: int | None = Field(default=None, ge=1888, le=2100)
    runtime: int | None = Field(default=None, gt=0)
    rating: float | None = Field(default=None, ge=0.0, le=10.0)


class GenreResponse(BaseModel):
    """Schema ответа с данными жанра."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
