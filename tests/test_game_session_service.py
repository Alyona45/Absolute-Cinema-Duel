import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from backend.actors import CurrentActor
from backend.models import SessionStatus
from backend.services.errors import (
    AccessDeniedError,
    AlreadyParticipantError,
    InvalidOperationError,
    SessionNotFoundError,
)
from backend.services.game_session_service import GameSessionService


class DummyDB:
    def rollback(self) -> None:
        return None


def _user_actor(user_id: int = 1) -> CurrentActor:
    return CurrentActor(
        user_id=user_id,
        guest_id=None,
        display_name=f"user-{user_id}",
        email=f"user-{user_id}@example.com",
    )


def test_join_by_invite_code_raises_when_session_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GameSessionService(DummyDB())

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_invite_code",
        lambda db, code: None,
    )

    with pytest.raises(SessionNotFoundError):
        service.join_by_invite_code("ABC123", actor=_user_actor())


def test_join_session_raises_when_already_participant(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GameSessionService(DummyDB())
    actor = _user_actor(2)

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_id",
        lambda db, session_id: SimpleNamespace(id=session_id, status=SessionStatus.CREATED),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.is_participant",
        lambda db, session_id, **kwargs: True,
    )

    with pytest.raises(AlreadyParticipantError):
        service.join_session(session_id=42, actor=actor)


def test_propose_movie_raises_for_non_participant(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GameSessionService(DummyDB())
    actor = _user_actor(2)

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_id",
        lambda db, session_id: SimpleNamespace(id=session_id),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_actor",
        lambda db, session_id, actor: None,
    )

    with pytest.raises(AccessDeniedError):
        service.propose_movie(session_id=42, movie_id=5, actor=actor)


def test_pick_winner_raises_when_not_host(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GameSessionService(DummyDB())
    actor = _user_actor(2)

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_id",
        lambda db, session_id: SimpleNamespace(id=session_id),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_actor",
        lambda db, session_id, actor: SimpleNamespace(id=7, is_host=False),
    )

    with pytest.raises(AccessDeniedError):
        service.pick_winner(session_id=42, winner_session_movie_id=100, actor=actor)


def test_join_session_raises_when_session_already_started(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GameSessionService(DummyDB())

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_id",
        lambda db, session_id: SimpleNamespace(id=session_id, status=SessionStatus.PLAYING),
    )

    with pytest.raises(InvalidOperationError):
        service.join_session(session_id=42, actor=_user_actor(2))


def test_select_movie_for_participant_raises_for_non_participant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GameSessionService(DummyDB())
    actor = _user_actor(2)

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_id",
        lambda db, session_id: SimpleNamespace(id=session_id, status=SessionStatus.CREATED),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_actor",
        lambda db, session_id, actor: None,
    )

    with pytest.raises(AccessDeniedError):
        service.select_movie_for_participant(session_id=42, actor=actor, session_movie_id=101)


def test_select_movie_for_participant_raises_for_foreign_movie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GameSessionService(DummyDB())
    actor = _user_actor(2)

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_id",
        lambda db, session_id: SimpleNamespace(id=session_id, status=SessionStatus.CREATED),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_actor",
        lambda db, session_id, actor: SimpleNamespace(id=7),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_session_movie_by_id",
        lambda db, session_movie_id: SimpleNamespace(id=session_movie_id, session_id=999),
    )

    with pytest.raises(InvalidOperationError):
        service.select_movie_for_participant(session_id=42, actor=actor, session_movie_id=101)


def test_pick_winner_by_participant_raises_when_not_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GameSessionService(DummyDB())
    actor = _user_actor(1)

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_id",
        lambda db, session_id: SimpleNamespace(id=session_id),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_actor",
        lambda db, session_id, actor: SimpleNamespace(id=7, is_host=False),
    )

    with pytest.raises(AccessDeniedError):
        service.pick_winner_by_participant(session_id=42, winner_participant_id=2, actor=actor)


def test_pick_winner_by_participant_raises_when_winner_not_participant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GameSessionService(DummyDB())
    actor = _user_actor(1)

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_id",
        lambda db, session_id: SimpleNamespace(id=session_id),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_actor",
        lambda db, session_id, actor: SimpleNamespace(id=7, is_host=True),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_id",
        lambda db, participant_id: None,
    )

    with pytest.raises(InvalidOperationError):
        service.pick_winner_by_participant(session_id=42, winner_participant_id=2, actor=actor)


def test_pick_winner_by_participant_raises_when_no_selected_movie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GameSessionService(DummyDB())
    actor = _user_actor(1)

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_id",
        lambda db, session_id: SimpleNamespace(id=session_id),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_actor",
        lambda db, session_id, actor: SimpleNamespace(id=7, is_host=True),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_id",
        lambda db, participant_id: SimpleNamespace(id=participant_id, session_id=42, selected_session_movie_id=None),
    )

    with pytest.raises(InvalidOperationError):
        service.pick_winner_by_participant(session_id=42, winner_participant_id=2, actor=actor)


def test_pick_winner_by_participant_uses_selected_movie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GameSessionService(DummyDB())
    actor = _user_actor(1)

    game_session = SimpleNamespace(id=42)
    winner_participant = SimpleNamespace(id=7, session_id=42, selected_session_movie_id=101)
    selected_movie = SimpleNamespace(id=101, session_id=42)
    expected_result = SimpleNamespace(id=42, winner_session_movie_id=101)

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_id",
        lambda db, session_id: game_session,
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_actor",
        lambda db, session_id, actor: SimpleNamespace(id=1, is_host=True),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_id",
        lambda db, participant_id: winner_participant,
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_session_movie_by_id",
        lambda db, session_movie_id: selected_movie,
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.set_winner",
        lambda db, gs, winner_session_movie_id: expected_result,
    )

    result = service.pick_winner_by_participant(
        session_id=42,
        winner_participant_id=2,
        actor=actor,
    )

    assert result is expected_result


def test_start_session_by_invite_code_requires_selected_movies_for_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GameSessionService(DummyDB())
    actor = _user_actor(1)

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_invite_code",
        lambda db, invite_code: SimpleNamespace(id=42, status=SessionStatus.CREATED),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_host_participant",
        lambda db, session_id: SimpleNamespace(id=1),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_actor",
        lambda db, session_id, actor: SimpleNamespace(id=1, is_host=True),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participants_by_session",
        lambda db, session_id: [
            SimpleNamespace(id=1, selected_session_movie_id=101),
            SimpleNamespace(id=2, selected_session_movie_id=None),
        ],
    )

    with pytest.raises(InvalidOperationError):
        service.start_session_by_invite_code(invite_code="ABC123", actor=actor)


def test_start_session_by_invite_code_raises_when_selected_movie_foreign(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GameSessionService(DummyDB())
    actor = _user_actor(1)

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_invite_code",
        lambda db, invite_code: SimpleNamespace(id=42, status=SessionStatus.CREATED),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_host_participant",
        lambda db, session_id: SimpleNamespace(id=1),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_actor",
        lambda db, session_id, actor: SimpleNamespace(id=1, is_host=True),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participants_by_session",
        lambda db, session_id: [SimpleNamespace(id=1, selected_session_movie_id=101)],
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_session_movie_by_id",
        lambda db, session_movie_id: SimpleNamespace(id=session_movie_id, session_id=999),
    )

    with pytest.raises(InvalidOperationError):
        service.start_session_by_invite_code(invite_code="ABC123", actor=actor)


def test_start_session_by_invite_code_requires_minimum_two_participants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GameSessionService(DummyDB())
    actor = _user_actor(1)

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_invite_code",
        lambda db, invite_code: SimpleNamespace(id=42, status=SessionStatus.CREATED),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_host_participant",
        lambda db, session_id: SimpleNamespace(id=1),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_actor",
        lambda db, session_id, actor: SimpleNamespace(id=1, is_host=True),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participants_by_session",
        lambda db, session_id: [SimpleNamespace(id=1, selected_session_movie_id=101)],
    )

    with pytest.raises(InvalidOperationError, match="минимум 2 участника"):
        service.start_session_by_invite_code(invite_code="ABC123", actor=actor)


def test_propose_movie_from_kinopoisk_handles_duplicate_movie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RollbackDB(DummyDB):
        def __init__(self) -> None:
            self.rollback_called = False

        def rollback(self) -> None:
            self.rollback_called = True

    db = RollbackDB()
    service = GameSessionService(db)
    actor = _user_actor(1)

    class DummyMovieService:
        def __init__(self, db_obj) -> None:
            self.db_obj = db_obj

        async def get_or_create_movie_by_kinopoisk_id(self, kinopoisk_id: int):
            return SimpleNamespace(id=777)

    monkeypatch.setattr(
        "backend.services.game_session_service.get_game_session_by_id",
        lambda db_obj, session_id: SimpleNamespace(id=session_id),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.get_participant_by_actor",
        lambda db_obj, session_id, actor_obj: SimpleNamespace(id=55),
    )
    monkeypatch.setattr(
        "backend.services.game_session_service.MovieService",
        DummyMovieService,
    )

    def _raise_integrity_error(db_obj, session_id, movie_id, participant_id):
        raise IntegrityError("insert", {}, Exception("duplicate key"))

    monkeypatch.setattr(
        "backend.services.game_session_service.add_movie_to_session",
        _raise_integrity_error,
    )

    async def _run() -> None:
        with pytest.raises(InvalidOperationError, match="уже добавлен"):
            await service.propose_movie_from_kinopoisk(
                session_id=42,
                kinopoisk_id=100500,
                actor=actor,
            )

    asyncio.run(_run())

    assert db.rollback_called is True
