import logging

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.actors import CurrentActor
from backend.models import SessionParticipant

logger = logging.getLogger(__name__)


def _commit(db: Session, action: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Ошибка БД при %s", action)
        raise


def get_participant_by_session_and_user(
    db: Session,
    session_id: int,
    user_id: int,
) -> SessionParticipant | None:
    return (
        db.query(SessionParticipant)
        .filter(
            SessionParticipant.session_id == session_id,
            SessionParticipant.user_id == user_id,
        )
        .first()
    )


def get_participant_by_session_and_guest(
    db: Session,
    session_id: int,
    guest_id: str,
) -> SessionParticipant | None:
    return (
        db.query(SessionParticipant)
        .filter(
            SessionParticipant.session_id == session_id,
            SessionParticipant.guest_id == guest_id,
        )
        .first()
    )


def get_participant_by_actor(
    db: Session,
    session_id: int,
    actor: CurrentActor,
) -> SessionParticipant | None:
    if actor.user_id is not None:
        return get_participant_by_session_and_user(db, session_id, actor.user_id)
    if actor.guest_id is None:
        return None
    return get_participant_by_session_and_guest(db, session_id, actor.guest_id)


def get_participant_by_id(db: Session, participant_id: int) -> SessionParticipant | None:
    return db.query(SessionParticipant).filter(SessionParticipant.id == participant_id).first()


def get_host_participant(db: Session, session_id: int) -> SessionParticipant | None:
    return (
        db.query(SessionParticipant)
        .filter(
            SessionParticipant.session_id == session_id,
            SessionParticipant.is_host.is_(True),
        )
        .first()
    )


def add_participant(
    db: Session,
    session_id: int,
    actor: CurrentActor,
    *,
    is_host: bool = False,
) -> SessionParticipant:
    participant = SessionParticipant(
        session_id=session_id,
        user_id=actor.user_id,
        guest_id=actor.guest_id,
        display_name=actor.display_name,
        is_host=is_host,
    )
    db.add(participant)
    _commit(db, "добавлении участника в сессию")
    db.refresh(participant)
    return participant


def remove_participant(db: Session, session_id: int, actor: CurrentActor) -> bool:
    participant = get_participant_by_actor(db, session_id, actor)
    if participant is None:
        return False

    db.delete(participant)
    _commit(db, "удалении участника из сессии")
    return True


def get_participants_by_session(db: Session, session_id: int) -> list[SessionParticipant]:
    return (
        db.query(SessionParticipant)
        .filter(SessionParticipant.session_id == session_id)
        .all()
    )


def is_participant(
    db: Session,
    session_id: int,
    *,
    user_id: int | None = None,
    guest_id: str | None = None,
) -> bool:
    filters = [SessionParticipant.session_id == session_id]
    identity_filters = []
    if user_id is not None:
        identity_filters.append(SessionParticipant.user_id == user_id)
    if guest_id is not None:
        identity_filters.append(SessionParticipant.guest_id == guest_id)
    if not identity_filters:
        return False

    return db.query(SessionParticipant).filter(*filters, or_(*identity_filters)).first() is not None


def set_selected_session_movie(
    db: Session,
    participant: SessionParticipant,
    session_movie_id: int,
) -> SessionParticipant:
    participant.selected_session_movie_id = session_movie_id
    _commit(db, "выборе фильма участником")
    db.refresh(participant)
    return participant
