from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.actors import CurrentActor, runtime_user_id_for_actor, runtime_user_id_for_participant
from backend.crud.game_session import (
    create_game_session,
    get_game_session_by_id,
    get_game_session_by_invite_code,
    get_sessions_by_user,
    set_winner,
    update_session_status,
)
from backend.crud.session_movie import (
    add_movie_to_session,
    get_movies_by_session,
    get_session_movie_by_id,
    remove_movie_from_session,
)
from backend.crud.session_participant import (
    add_participant,
    get_host_participant,
    get_participant_by_actor,
    get_participant_by_id,
    get_participants_by_session,
    is_participant,
    remove_participant,
    set_selected_session_movie,
)
from backend.models import GameSession, SessionMovie, SessionParticipant, SessionStatus
from backend.services.errors import (
    AccessDeniedError,
    AlreadyParticipantError,
    InvalidOperationError,
    ParticipantNotFoundError,
    SessionMovieNotFoundError,
    SessionNotFoundError,
)
from backend.services.movie_service import MovieService
from backend.websocket.room import RoomManager
from backend.websocket.models import Participant


class GameSessionService:
    def __init__(self, db: Session, room_manager: RoomManager | None = None) -> None:
        self.db = db
        self._room_manager = room_manager

    # ─────────────────── room_manager sync helpers ───────────────────

    def _sync_create_room(self, session: GameSession, host_actor: CurrentActor) -> None:
        """Создаёт in-memory комнату при создании сессии."""
        if self._room_manager is None:
            return
        room_id = str(session.id)
        # Комната могла уже существовать (повторный вызов) — тогда пропускаем
        if self._room_manager.get_room(room_id) is not None:
            return
        host_user_id = runtime_user_id_for_actor(host_actor)
        if host_actor.is_guest:
            participant = Participant.guest(host_actor.display_name)
        else:
            participant = Participant.authenticated(
                host_actor.display_name, email=host_actor.email
            )
        from backend.websocket.models import Room
        room = Room(
            host_user_id=host_user_id,
            participants={host_user_id: participant},
        )
        self._room_manager.rooms[room_id] = room

    def _sync_join_room(self, session_id: int, actor: CurrentActor) -> None:
        """Добавляет участника в in-memory комнату при join_session."""
        if self._room_manager is None:
            return
        room_id = str(session_id)
        room = self._room_manager.get_room(room_id)
        if room is None:
            return
        user_id = runtime_user_id_for_actor(actor)
        if user_id in room.participants:
            return
        if actor.is_guest:
            participant = Participant.guest(actor.display_name)
        else:
            participant = Participant.authenticated(
                actor.display_name, email=actor.email
            )
        room.add_participant(user_id, participant)

    def _sync_start_game(self, session_id: int) -> None:
        """Переводит in-memory комнату в статус PLAYING."""
        if self._room_manager is None:
            return
        self._room_manager.start_game(str(session_id))

    # ─────────────────── Public API ───────────────────────────────────

    def create_session(self, host_actor: CurrentActor) -> GameSession:
        session = create_game_session(self.db, host_actor=host_actor)
        self._sync_create_room(session, host_actor)
        return session

    def get_session(self, session_id: int) -> GameSession:
        game_session = get_game_session_by_id(self.db, session_id)
        if game_session is None:
            raise SessionNotFoundError("Игровая сессия не найдена")
        return game_session

    def list_my_sessions(self, user_id: int, skip: int = 0, limit: int = 50) -> list[GameSession]:
        return get_sessions_by_user(self.db, user_id=user_id, skip=skip, limit=limit)

    def join_by_invite_code(self, invite_code: str, actor: CurrentActor) -> SessionParticipant:
        game_session = get_game_session_by_invite_code(self.db, invite_code)
        if game_session is None:
            raise SessionNotFoundError("Игровая сессия не найдена")
        return self.join_session(game_session.id, actor)

    def get_session_by_invite_code(self, invite_code: str) -> GameSession:
        game_session = get_game_session_by_invite_code(self.db, invite_code)
        if game_session is None:
            raise SessionNotFoundError("Игровая сессия не найдена")
        return game_session

    def join_session(self, session_id: int, actor: CurrentActor) -> SessionParticipant:
        game_session = self.get_session(session_id)
        if game_session.status != SessionStatus.CREATED:
            raise InvalidOperationError("В сессию нельзя войти после её запуска или завершения")

        if is_participant(
            self.db,
            session_id,
            user_id=actor.user_id,
            guest_id=actor.guest_id,
        ):
            raise AlreadyParticipantError("Вы уже являетесь участником этой сессии")

        try:
            db_participant = add_participant(self.db, session_id, actor)
        except IntegrityError as exc:
            self.db.rollback()
            raise AlreadyParticipantError("Вы уже являетесь участником этой сессии") from exc

        self._sync_join_room(session_id, actor)
        return db_participant

    def leave_session(self, session_id: int, actor: CurrentActor) -> None:
        removed = remove_participant(self.db, session_id, actor)
        if not removed:
            raise ParticipantNotFoundError("Вы не являетесь участником этой сессии")

    def list_participants(self, session_id: int) -> list[SessionParticipant]:
        self.get_session(session_id)
        return get_participants_by_session(self.db, session_id)

    def start_game(self, session_id: int, actor: CurrentActor) -> GameSession:
        """
        Переводит сессию в статус PLAYING (этап игры).
        Только хост может инициировать старт игры.
        """
        game_session = self.get_session(session_id)
        participant = self.require_participant(session_id, actor)
        if not participant.is_host:
            raise AccessDeniedError("Только хост может начать игру")
        if game_session.status != SessionStatus.CREATED:
            raise InvalidOperationError("Игру можно начать только из статуса CREATED")
        result = update_session_status(self.db, game_session, SessionStatus.PLAYING)
        self._sync_start_game(session_id)
        return result

    def propose_movie(self, session_id: int, movie_id: int, actor: CurrentActor) -> SessionMovie:
        self.get_session(session_id)
        participant = self.require_participant(session_id, actor)
        return add_movie_to_session(self.db, session_id, movie_id, participant.id)

    async def propose_movie_from_kinopoisk(
        self,
        session_id: int,
        kinopoisk_id: int,
        actor: CurrentActor,
    ) -> SessionMovie:
        self.get_session(session_id)
        participant = self.require_participant(session_id, actor)

        movie_service = MovieService(self.db)
        movie = await movie_service.get_or_create_movie_by_kinopoisk_id(kinopoisk_id)
        try:
            return add_movie_to_session(self.db, session_id, movie.id, participant.id)
        except IntegrityError as exc:
            self.db.rollback()
            raise InvalidOperationError("Фильм уже добавлен в игровую сессию") from exc

    def retract_movie(self, session_id: int, session_movie_id: int, actor: CurrentActor) -> None:
        session_movie = get_session_movie_by_id(self.db, session_movie_id)
        if session_movie is None or session_movie.session_id != session_id:
            raise SessionMovieNotFoundError("Фильм не найден в этой сессии")

        participant = self.require_participant(session_id, actor)
        if participant.id != session_movie.proposed_by_participant_id and not participant.is_host:
            raise AccessDeniedError("Нет прав на удаление этого фильма из сессии")

        remove_movie_from_session(self.db, session_movie_id)

    def list_session_movies(self, session_id: int) -> list[SessionMovie]:
        self.get_session(session_id)
        return get_movies_by_session(self.db, session_id)

    def select_movie_for_participant(
        self,
        session_id: int,
        actor: CurrentActor,
        session_movie_id: int,
    ) -> SessionParticipant:
        game_session = self.get_session(session_id)
        if game_session.status != SessionStatus.CREATED:
            raise InvalidOperationError("Выбор фильма доступен только до старта сессии")

        participant = self.require_participant(session_id, actor)

        session_movie = get_session_movie_by_id(self.db, session_movie_id)
        if session_movie is None or session_movie.session_id != session_id:
            raise InvalidOperationError("Выбранный фильм не принадлежит этой сессии")

        return set_selected_session_movie(self.db, participant, session_movie_id)

    def start_session_by_invite_code(self, invite_code: str, actor: CurrentActor) -> GameSession:
        game_session = self.get_session_by_invite_code(invite_code)
        if game_session.status != SessionStatus.CREATED:
            raise InvalidOperationError("Игровая сессия уже запущена или завершена")

        host_participant = get_host_participant(self.db, game_session.id)
        if host_participant is None:
            raise InvalidOperationError("Хост игровой сессии не найден")

        participant = self.require_participant(game_session.id, actor)
        if participant.id != host_participant.id:
            raise AccessDeniedError("Только хост может запустить игровую сессию")

        participants = get_participants_by_session(self.db, game_session.id)
        if len(participants) < 2:
            raise InvalidOperationError("Для старта необходимо минимум 2 участника")

        participants_without_selection = [
            p.id for p in participants if p.selected_session_movie_id is None
        ]
        if participants_without_selection:
            raise InvalidOperationError(
                "Перед стартом игры каждый участник должен выбрать фильм"
            )

        for p in participants:
            selected_movie = get_session_movie_by_id(self.db, p.selected_session_movie_id)
            if selected_movie is None or selected_movie.session_id != game_session.id:
                raise InvalidOperationError(
                    "Выбранный участником фильм должен принадлежать текущей сессии"
                )

        result = update_session_status(self.db, game_session, SessionStatus.PLAYING)
        self._sync_start_game(game_session.id)
        return result

    def pick_winner(
        self,
        session_id: int,
        winner_session_movie_id: int,
        actor: CurrentActor,
    ) -> GameSession:
        game_session = self.get_session(session_id)
        participant = self.require_participant(session_id, actor)
        if not participant.is_host:
            raise AccessDeniedError("Только хост может выбрать победителя")

        session_movie = get_session_movie_by_id(self.db, winner_session_movie_id)
        if session_movie is None or session_movie.session_id != session_id:
            raise InvalidOperationError("Указанный фильм не принадлежит данной сессии")

        return set_winner(self.db, game_session, winner_session_movie_id)

    def pick_winner_by_participant(
        self,
        session_id: int,
        winner_participant_id: int,
        actor: CurrentActor,
    ) -> GameSession:
        game_session = self.get_session(session_id)
        current_participant = self.require_participant(session_id, actor)
        if not current_participant.is_host:
            raise AccessDeniedError("Только хост может выбрать победителя")

        participant = get_participant_by_id(self.db, winner_participant_id)
        if participant is None or participant.session_id != session_id:
            raise InvalidOperationError("Победитель должен быть участником этой сессии")

        selected_session_movie_id = participant.selected_session_movie_id
        if selected_session_movie_id is None:
            raise InvalidOperationError("У победителя не выбран фильм")

        selected_movie = get_session_movie_by_id(self.db, selected_session_movie_id)
        if selected_movie is None or selected_movie.session_id != session_id:
            raise InvalidOperationError(
                "Выбранный победителем фильм не принадлежит этой сессии"
            )

        return set_winner(self.db, game_session, selected_session_movie_id)

    def require_participant(self, session_id: int, actor: CurrentActor) -> SessionParticipant:
        participant = get_participant_by_actor(self.db, session_id, actor)
        if participant is None:
            raise AccessDeniedError("Только участники сессии могут выполнить это действие")
        return participant