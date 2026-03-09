from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models import GameSession, SessionStatus


def create_game_session(db: Session, host_user_id: int) -> GameSession:
    """
    Создаёт новую игровую сессию.
    Статус по умолчанию — CREATED, время старта проставляется автоматически.
    """
    session = GameSession(host_user_id=host_user_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_game_session_by_id(db: Session, session_id: int) -> GameSession | None:
    """Возвращает игровую сессию по первичному ключу или None."""
    return db.query(GameSession).filter(GameSession.id == session_id).first()


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

    db.commit()
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

    db.commit()
    db.refresh(game_session)
    return game_session
