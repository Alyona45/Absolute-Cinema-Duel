from sqlalchemy.orm import Session

from backend.models import SessionParticipant, User


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
    db.commit()
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
    db.commit()
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
