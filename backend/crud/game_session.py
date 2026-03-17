from datetime import datetime, timezone
import logging
import secrets
import string

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models import GameSession, SessionParticipant, SessionStatus

logger = logging.getLogger(__name__)
INVITE_CODE_ALPHABET = string.ascii_uppercase + string.digits
INVITE_CODE_LENGTH = 6
MAX_INVITE_CODE_ATTEMPTS = 10


def _commit(db: Session, action: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Ошибка БД при %s", action)
        raise


def create_game_session(db: Session, host_user_id: int) -> GameSession:
    """
    Создаёт новую игровую сессию.
    Статус по умолчанию — CREATED, время старта проставляется автоматически.
    Хост автоматически добавляется в состав участников.
    """
    for _ in range(MAX_INVITE_CODE_ATTEMPTS):
        invite_code = _generate_invite_code()
        if get_game_session_by_invite_code(db, invite_code) is not None:
            continue

        session = GameSession(host_user_id=host_user_id, invite_code=invite_code)
        db.add(session)
        db.flush()
        db.add(SessionParticipant(session_id=session.id, user_id=host_user_id))
        _commit(db, "создании игровой сессии")
        db.refresh(session)
        return session

    raise RuntimeError("Не удалось сгенерировать уникальный invite_code для игровой сессии")


def get_game_session_by_id(db: Session, session_id: int) -> GameSession | None:
    """Возвращает игровую сессию по первичному ключу или None."""
    return db.query(GameSession).filter(GameSession.id == session_id).first()


def get_game_session_by_invite_code(
    db: Session,
    invite_code: str,
) -> GameSession | None:
    """Возвращает игровую сессию по invite_code или None."""
    normalized_code = invite_code.strip().upper()
    return (
        db.query(GameSession)
        .filter(GameSession.invite_code == normalized_code)
        .first()
    )


def get_sessions_by_user(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
) -> list[GameSession]:
    """
    Возвращает все сессии, где указанный пользователь является хостом.
    Поддерживает пагинацию через skip/limit.
    """
    return (
        db.query(GameSession)
        .filter(GameSession.host_user_id == user_id)
        .order_by(GameSession.started_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_session_status(
    db: Session,
    game_session: GameSession,
    new_status: SessionStatus,
) -> GameSession:
    """
    Обновляет статус игровой сессии.
    Если новый статус — FINISHED или CANCELLED, автоматически
    проставляется время завершения (finished_at).
    """
    game_session.status = new_status

    # Фиксируем время завершения для конечных статусов
    if new_status in (SessionStatus.FINISHED, SessionStatus.CANCELLED):
        game_session.finished_at = datetime.now(timezone.utc)

    _commit(db, "обновлении статуса игровой сессии")
    db.refresh(game_session)
    return game_session


def set_winner(
    db: Session,
    game_session: GameSession,
    winner_session_movie_id: int,
) -> GameSession:
    """
    Записывает фильм-победитель и завершает сессию.
    — Устанавливает winner_session_movie_id.
    — Переводит статус в FINISHED.
    — Проставляет finished_at.
    """
    game_session.winner_session_movie_id = winner_session_movie_id
    game_session.status = SessionStatus.FINISHED
    game_session.finished_at = datetime.now(timezone.utc)

    _commit(db, "установке победителя игровой сессии")
    db.refresh(game_session)
    return game_session


def _generate_invite_code() -> str:
    return "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))
