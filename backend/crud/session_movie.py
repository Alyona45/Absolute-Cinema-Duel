import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models import SessionMovie

logger = logging.getLogger(__name__)


def _commit(db: Session, action: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Ошибка БД при %s", action)
        raise


def add_movie_to_session(
    db: Session,
    session_id: int,
    movie_id: int,
    proposed_by_user_id: int,
) -> SessionMovie:
    """
    Добавляет фильм в игровую сессию от имени участника.
    Уникальность пары (session_id, movie_id) обеспечивается индексом —
    один и тот же фильм нельзя предложить дважды в рамках одной сессии.
    """
    session_movie = SessionMovie(
        session_id=session_id,
        movie_id=movie_id,
        proposed_by_user_id=proposed_by_user_id,
    )
    db.add(session_movie)
    _commit(db, "добавлении фильма в сессию")
    db.refresh(session_movie)
    return session_movie


def remove_movie_from_session(db: Session, session_movie_id: int) -> bool:
    """
    Удаляет предложенный фильм из сессии по ID записи.
    Возвращает True, если запись найдена и удалена, иначе False.
    """
    session_movie = (
        db.query(SessionMovie).filter(SessionMovie.id == session_movie_id).first()
    )
    if session_movie is None:
        return False

    db.delete(session_movie)
    _commit(db, "удалении фильма из сессии")
    return True


def get_movies_by_session(db: Session, session_id: int) -> list[SessionMovie]:
    """Возвращает все фильмы, предложенные в указанной сессии."""
    return (
        db.query(SessionMovie)
        .filter(SessionMovie.session_id == session_id)
        .all()
    )


def get_session_movie_by_id(db: Session, session_movie_id: int) -> SessionMovie | None:
    """
    Возвращает запись SessionMovie по первичному ключу.
    Используется, например, при назначении победителя.
    """
    return db.query(SessionMovie).filter(SessionMovie.id == session_movie_id).first()
