from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.actors import CurrentActor
from backend import models
from backend.database import get_db
from backend.schemas.game_session import (
    GameSessionResponse,
    JoinSessionByCodeRequest,
    SelectParticipantMovieRequest,
    SelectWinnerParticipantRequest,
    SessionMovieResponse,
    SessionParticipantResponse,
)
from backend.schemas.movie import AddMovieFromKinopoiskRequest
from backend.security import ensure_guest_actor, get_current_actor, get_current_actor_optional, get_current_user
from backend.services.errors import (
    AccessDeniedError,
    AlreadyParticipantError,
    InvalidOperationError,
    MovieNotFoundError,
    ParticipantNotFoundError,
    SessionMovieNotFoundError,
    SessionNotFoundError,
)
from backend.services.game_session_service import GameSessionService
# Импортируем синглтон room_manager из ws.py — он живёт всё время работы сервера
from backend.routers.ws import room_manager

router = APIRouter(prefix="/sessions", tags=["game sessions"])


# ─────────────────── Вспомогательная зависимость ───────────────────


def get_game_session_service(db: Session = Depends(get_db)) -> GameSessionService:
    # Передаём room_manager чтобы сервис синхронизировал in-memory состояние
    return GameSessionService(db, room_manager=room_manager)


# ─────────────────────── Игровые сессии ───────────────────────

@router.post("/{session_id}/start-game", response_model=GameSessionResponse)
def start_game(
    session_id: int,
    current_actor: Annotated[CurrentActor, Depends(get_current_actor)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> GameSessionResponse:
    """
    Переводит сессию в статус PLAYING (этап игры). Пока всегда запускает Flappy Bird.
    В будущем здесь будет выбор типа игры.
    Только хост может инициировать старт игры.
    """
    try:
        session = service.start_game(session_id, current_actor)
        return session
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InvalidOperationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    
@router.post(
    "/",
    response_model=GameSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    response: Response,
    current_actor: Annotated[CurrentActor | None, Depends(get_current_actor_optional)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> GameSessionResponse:
    """Создаёт новую игровую сессию. Текущий actor становится хостом."""
    actor = ensure_guest_actor(response, current_actor)
    return service.create_session(host_actor=actor)


@router.post(
    "/join-by-code",
    response_model=SessionParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
def join_session_by_code(
    body: JoinSessionByCodeRequest,
    response: Response,
    current_actor: Annotated[CurrentActor | None, Depends(get_current_actor_optional)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> SessionParticipantResponse:
    """Присоединяется к сессии по invite-коду."""
    actor = ensure_guest_actor(response, current_actor)
    try:
        return service.join_by_invite_code(invite_code=body.invite_code, actor=actor)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AlreadyParticipantError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidOperationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/", response_model=list[GameSessionResponse])
def list_my_sessions(
    current_actor: Annotated[CurrentActor, Depends(get_current_actor)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> list[GameSessionResponse]:
    """Возвращает список сессий текущего пользователя."""
    if current_actor.user_id is None:
        return []
    return service.list_my_sessions(current_actor.user_id)


@router.get("/{session_id}", response_model=GameSessionResponse)
def get_session(
    session_id: int,
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> GameSessionResponse:
    try:
        return service.get_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{session_id}/participants", response_model=list[SessionParticipantResponse])
def list_participants(
    session_id: int,
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> list[SessionParticipantResponse]:
    try:
        return service.list_participants(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{session_id}/movies",
    response_model=SessionMovieResponse,
    status_code=status.HTTP_201_CREATED,
)
def propose_movie(
    session_id: int,
    body: AddMovieFromKinopoiskRequest,
    current_actor: Annotated[CurrentActor, Depends(get_current_actor)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> SessionMovieResponse:
    try:
        return service.propose_movie(session_id, body.movie_id, current_actor)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{session_id}/movies", response_model=list[SessionMovieResponse])
def list_session_movies(
    session_id: int,
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> list[SessionMovieResponse]:
    try:
        return service.list_session_movies(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{session_id}/movies/{session_movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def retract_movie(
    session_id: int,
    session_movie_id: int,
    current_actor: Annotated[CurrentActor, Depends(get_current_actor)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> None:
    try:
        service.retract_movie(session_id, session_movie_id, current_actor)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SessionMovieNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/{session_id}/select-movie", response_model=SessionParticipantResponse)
def select_movie(
    session_id: int,
    body: SelectParticipantMovieRequest,
    current_actor: Annotated[CurrentActor, Depends(get_current_actor)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> SessionParticipantResponse:
    try:
        return service.select_movie_for_participant(
            session_id, current_actor, body.session_movie_id
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InvalidOperationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{session_id}/winner", response_model=GameSessionResponse)
def pick_winner(
    session_id: int,
    body: SelectWinnerParticipantRequest,
    current_actor: Annotated[CurrentActor, Depends(get_current_actor)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> GameSessionResponse:
    try:
        return service.pick_winner_by_participant(
            session_id, body.winner_participant_id, current_actor
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InvalidOperationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{session_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_session(
    session_id: int,
    current_actor: Annotated[CurrentActor, Depends(get_current_actor)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> None:
    try:
        service.leave_session(session_id, current_actor)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ParticipantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc