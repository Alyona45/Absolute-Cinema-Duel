import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models import SessionParticipant

logger = logging.getLogger(__name__)


def _commit(db: Session, action: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Ошибка БД при %s", action)
        raise


def _get_participant(db: Session, session_id: int, user_id: int) -> SessionParticipant | None:
    """Внутренний хелпер: находит участника по паре (session_id, user_id)."""
    return (
        db.query(SessionParticipant)
        .filter(
            SessionParticipant.session_id == session_id,
            SessionParticipant.user_id == user_id,
        )
        .first()
    )


def add_participant(db: Session, session_id: int, user_id: int) -> SessionParticipant:
    """
    Добавляет пользователя в игровую сессию.
    Уникальность пары (session_id, user_id) обеспечивается индексом в БД —
    при дублировании будет ошибка IntegrityError.
    """
    participant = SessionParticipant(session_id=session_id, user_id=user_id)
    db.add(participant)
    _commit(db, "добавлении участника в сессию")
    db.refresh(participant)
    return participant


def remove_participant(db: Session, session_id: int, user_id: int) -> bool:
    """
    Удаляет пользователя из игровой сессии.
    Возвращает True, если участник был найден и удалён, иначе False.
    """
    participant = _get_participant(db, session_id, user_id)
    if participant is None:
        return False

    db.delete(participant)
    _commit(db, "удалении участника из сессии")
    return True


def get_participants_by_session(db: Session, session_id: int) -> list[SessionParticipant]:
    """Возвращает список всех участников указанной игровой сессии."""
    return (
        db.query(SessionParticipant)
        .filter(SessionParticipant.session_id == session_id)
        .all()
    )


def is_participant(db: Session, session_id: int, user_id: int) -> bool:
    """
    Проверяет, является ли пользователь участником сессии.
    Возвращает True, если запись найдена, иначе False.
    """
    return _get_participant(db, session_id, user_id) is not None
