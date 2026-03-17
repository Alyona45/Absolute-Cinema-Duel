from datetime import datetime, timezone

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from pydantic import field_validator


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


class MovieSearchResult(BaseModel):
    """Краткий результат поиска фильма во внешнем API."""

    kinopoisk_id: int
    title: str
    year: int | None = None
    poster_url: str | None = None


class AddMovieFromKinopoiskRequest(BaseModel):
    """Schema запроса для добавления фильма в сессию по kinopoisk_id."""

    kinopoisk_id: int


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
    genres: list["MovieGenreResponse"] = Field(default_factory=list, validation_alias="genre_links")
    cached_at: AwareDatetime

    @field_validator("cached_at", mode="before")
    @classmethod
    def ensure_cached_at_is_aware(cls, value: object) -> object:
        if isinstance(value, datetime) and (value.tzinfo is None or value.utcoffset() is None):
            return value.replace(tzinfo=timezone.utc)
        return value


class MovieUpdate(BaseModel):
    """Schema для обновления кеша фильма. Все поля опциональны."""

    kinopoisk_id: int | None = None
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


class MovieGenreResponse(BaseModel):
    """Schema связи фильма с жанром для сериализации ORM relationship."""

    model_config = ConfigDict(from_attributes=True)

    genre: GenreResponse
