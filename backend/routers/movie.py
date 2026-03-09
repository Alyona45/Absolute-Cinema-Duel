from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend import models
from backend.database import get_db
from backend.schemas.movie import GenreResponse, MovieCreate, MovieResponse, MovieUpdate
from backend.crud.movie import (
    get_movie_by_id,
    get_movie_by_kinopoisk_id,
    get_or_create_movie,
    update_movie_cache,
    get_all_genres,
    get_genres_by_movie,
    sync_movie_genres,
)
from backend.security import get_current_user

router = APIRouter(prefix="/movies", tags=["movies"])


# ─────────────────────────── Фильмы ───────────────────────────


@router.post(
    "/",
    response_model=MovieResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_or_get_movie(
    movie_data: MovieCreate,
    db: Session = Depends(get_db),
    _: Annotated[models.User, Depends(get_current_user)] = None,
) -> MovieResponse:
    """
    Создаёт (кеширует) фильм из данных внешнего API, либо
    возвращает уже существующий по kinopoisk_id.
    Требуется авторизация.
    """
    return get_or_create_movie(db, movie_data)


@router.get("/{movie_id}", response_model=MovieResponse)
def read_movie(
    movie_id: int,
    db: Session = Depends(get_db),
) -> MovieResponse:
    """Возвращает фильм по внутреннему ID."""
    movie = get_movie_by_id(db, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фильм не найден",
        )
    return movie


@router.get("/kinopoisk/{kinopoisk_id}", response_model=MovieResponse)
def read_movie_by_kinopoisk(
    kinopoisk_id: int,
    db: Session = Depends(get_db),
) -> MovieResponse:
    """Возвращает фильм по ID Кинопоиска."""
    movie = get_movie_by_kinopoisk_id(db, kinopoisk_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фильм с таким kinopoisk_id не найден",
        )
    return movie


@router.patch("/{movie_id}", response_model=MovieResponse)
def update_movie(
    movie_id: int,
    update_data: MovieUpdate,
    db: Session = Depends(get_db),
    _: Annotated[models.User, Depends(get_current_user)] = None,
) -> MovieResponse:
    """Обновляет кешированные данные фильма. Требуется авторизация."""
    movie = get_movie_by_id(db, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фильм не найден",
        )
    return update_movie_cache(db, movie, update_data)


# ─────────────────────────── Жанры ───────────────────────────


@router.get("/{movie_id}/genres", response_model=list[GenreResponse])
def read_movie_genres(
    movie_id: int,
    db: Session = Depends(get_db),
) -> list[GenreResponse]:
    """Возвращает список жанров указанного фильма."""
    movie = get_movie_by_id(db, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фильм не найден",
        )
    return get_genres_by_movie(db, movie_id)


@router.put("/{movie_id}/genres", response_model=list[GenreResponse])
def replace_movie_genres(
    movie_id: int,
    genre_names: list[str],
    db: Session = Depends(get_db),
    _: Annotated[models.User, Depends(get_current_user)] = None,
) -> list[GenreResponse]:
    """
    Полностью синхронизирует жанры фильма с переданным списком.
    Добавляет недостающие, удаляет лишние. Требуется авторизация.
    """
    movie = get_movie_by_id(db, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фильм не найден",
        )
    return sync_movie_genres(db, movie_id, genre_names)


@router.get("/genres/all", response_model=list[GenreResponse])
def list_all_genres(db: Session = Depends(get_db)) -> list[GenreResponse]:
    """Возвращает список всех жанров в базе."""
    return get_all_genres(db)
