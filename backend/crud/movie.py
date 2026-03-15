from datetime import datetime, timezone
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models import Genre, Movie, MovieGenre
from backend.schemas.movie import MovieCreate, MovieUpdate

logger = logging.getLogger(__name__)


def _commit(db: Session, action: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Ошибка БД при %s", action)
        raise


def get_movie_by_id(db: Session, movie_id: int) -> Movie | None:
    """Возвращает фильм по первичному ключу или None, если не найден."""
    return db.query(Movie).filter(Movie.id == movie_id).first()


def get_movie_by_kinopoisk_id(db: Session, kinopoisk_id: int) -> Movie | None:
    """Возвращает фильм по ID Кинопоиска или None, если не найден."""
    return db.query(Movie).filter(Movie.kinopoisk_id == kinopoisk_id).first()


def get_or_create_movie(db: Session, movie_data: MovieCreate) -> Movie:
    """
    Возвращает существующий фильм по kinopoisk_id, либо создаёт новый.
    Основная точка входа при кешировании данных из внешнего API —
    если фильм уже есть в БД, повторно не создаётся.
    """
    existing = get_movie_by_kinopoisk_id(db, movie_data.kinopoisk_id)
    if existing:
        return existing

    db_movie = Movie(
        kinopoisk_id=movie_data.kinopoisk_id,
        title=movie_data.title,
        description=movie_data.description,
        poster_url=movie_data.poster_url,
        year=movie_data.year,
        runtime=movie_data.runtime,
        rating=movie_data.rating,
    )
    db.add(db_movie)
    _commit(db, "создании фильма")
    db.refresh(db_movie)
    return db_movie


def update_movie_cache(db: Session, movie: Movie, update_data: MovieUpdate) -> Movie:
    """
    Обновляет кешированные поля фильма (рейтинг, постер и т.д.).
    Обновляются только явно переданные поля (не None).
    Также обновляется метка cached_at, чтобы отразить свежесть кеша.
    """
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(movie, field, value)

    # Обновляем время кеширования при каждом обновлении данных
    movie.cached_at = datetime.now(timezone.utc)

    _commit(db, "обновлении кеша фильма")
    db.refresh(movie)
    return movie


# ─────────────────────────── Жанры ───────────────────────────


def get_or_create_genre(db: Session, name: str) -> Genre:
    """
    Возвращает жанр по имени или создаёт новый.
    Использует flush() вместо commit() для атомарности в рамках общей транзакции.
    """
    genre = db.query(Genre).filter(Genre.name == name).first()
    if genre:
        return genre

    genre = Genre(name=name)
    db.add(genre)
    db.flush()
    return genre


def get_all_genres(db: Session) -> list[Genre]:
    """Возвращает список всех жанров в базе."""
    return db.query(Genre).all()


def get_genres_by_movie(db: Session, movie_id: int) -> list[Genre]:
    """
    Возвращает список жанров, привязанных к указанному фильму.
    Использует join через таблицу movie_genres.
    """
    return (
        db.query(Genre)
        .join(MovieGenre, MovieGenre.genre_id == Genre.id)
        .filter(MovieGenre.movie_id == movie_id)
        .all()
    )


def sync_movie_genres(db: Session, movie_id: int, genre_names: list[str]) -> list[Genre]:
    """
    Синхронизирует жанры фильма с переданным списком названий.
    — Создаёт недостающие жанры в таблице genres.
    — Добавляет новые связи в movie_genres.
    — Удаляет связи, которых нет в переданном списке.
    Возвращает итоговый список жанров фильма.
    """
    # Получаем или создаём все нужные жанры
    target_genres = [get_or_create_genre(db, name) for name in genre_names]
    target_genre_ids = {g.id for g in target_genres}

    # Текущие связи фильм-жанр
    existing_links = (
        db.query(MovieGenre).filter(MovieGenre.movie_id == movie_id).all()
    )
    existing_genre_ids = {link.genre_id for link in existing_links}

    # Добавляем недостающие связи
    to_add = target_genre_ids - existing_genre_ids
    for genre_id in to_add:
        db.add(MovieGenre(movie_id=movie_id, genre_id=genre_id))

    # Удаляем лишние связи
    to_remove = existing_genre_ids - target_genre_ids
    if to_remove:
        db.query(MovieGenre).filter(
            MovieGenre.movie_id == movie_id,
            MovieGenre.genre_id.in_(to_remove),
        ).delete(synchronize_session="fetch")

    _commit(db, "синхронизации жанров фильма")
    return target_genres
