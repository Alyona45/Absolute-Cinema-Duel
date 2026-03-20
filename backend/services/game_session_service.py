from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.actors import CurrentActor
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


class GameSessionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(self, host_actor: CurrentActor) -> GameSession:
        return create_game_session(self.db, host_actor=host_actor)

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
            return add_participant(self.db, session_id, actor)
        except IntegrityError as exc:
            self.db.rollback()
            raise AlreadyParticipantError("Вы уже являетесь участником этой сессии") from exc

    def leave_session(self, session_id: int, actor: CurrentActor) -> None:
        removed = remove_participant(self.db, session_id, actor)
        if not removed:
            raise ParticipantNotFoundError("Вы не являетесь участником этой сессии")

    def list_participants(self, session_id: int) -> list[SessionParticipant]:
        self.get_session(session_id)
        return get_participants_by_session(self.db, session_id)

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

        return add_movie_to_session(self.db, session_id, movie.id, participant.id)

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
        participants_without_selection = [
            participant.id
            for participant in participants
            if participant.selected_session_movie_id is None
        ]
        if participants_without_selection:
            raise InvalidOperationError(
                "Перед стартом игры каждый участник должен выбрать фильм"
            )

        for participant in participants:
            selected_movie = get_session_movie_by_id(
                self.db,
                participant.selected_session_movie_id,
            )
            if selected_movie is None or selected_movie.session_id != game_session.id:
                raise InvalidOperationError(
                    "Выбранный участником фильм должен принадлежать текущей сессии"
                )

        return update_session_status(self.db, game_session, SessionStatus.PLAYING)

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
            raise InvalidOperationError("Выбранный победителем фильм не принадлежит этой сессии")

        return set_winner(self.db, game_session, selected_session_movie_id)

    def require_participant(self, session_id: int, actor: CurrentActor) -> SessionParticipant:
        participant = get_participant_by_actor(self.db, session_id, actor)
        if participant is None:
            raise AccessDeniedError("Только участники сессии могут выполнить это действие")
        return participant
