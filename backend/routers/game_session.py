from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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
from backend.security import get_current_user
from backend.services.errors import (
    AccessDeniedError,
    AlreadyParticipantError,
    InvalidOperationError,
    ParticipantNotFoundError,
    SessionMovieNotFoundError,
    SessionNotFoundError,
)
from backend.services.game_session_service import GameSessionService

router = APIRouter(prefix="/sessions", tags=["game sessions"])


# ─────────────────── Вспомогательная зависимость ───────────────────


def get_game_session_service(db: Session = Depends(get_db)) -> GameSessionService:
    return GameSessionService(db)


# ─────────────────────── Игровые сессии ───────────────────────


@router.post(
    "/",
    response_model=GameSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    current_user: Annotated[models.User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> GameSessionResponse:
    """Создаёт новую игровую сессию. Текущий пользователь становится хостом."""
    return service.create_session(host_user_id=current_user.id)


@router.post(
    "/join-by-code",
    response_model=SessionParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
def join_session_by_code(
    body: JoinSessionByCodeRequest,
    current_user: Annotated[models.User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> SessionParticipantResponse:
    """Добавляет текущего пользователя в сессию по invite_code."""
    try:
        return service.join_by_invite_code(body.invite_code, current_user.id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidOperationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AlreadyParticipantError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/my/list", response_model=list[GameSessionResponse])
def list_my_sessions(
    current_user: Annotated[models.User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
    skip: int = 0,
    limit: int = 50,
) -> list[GameSessionResponse]:
    """Возвращает сессии, где текущий пользователь — хост."""
    return service.list_my_sessions(current_user.id, skip, limit)


@router.get("/{session_id}", response_model=GameSessionResponse)
def read_session(
    session_id: int,
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
    _: Annotated[models.User, Depends(get_current_user)] = None,
) -> GameSessionResponse:
    """Возвращает данные игровой сессии по ID."""
    try:
        return service.get_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{session_id}/winner", response_model=GameSessionResponse)
def pick_winner(
    session_id: int,
    winner_session_movie_id: int,
    current_user: Annotated[models.User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> GameSessionResponse:
    """
    Назначает фильм-победитель и завершает сессию.
    Только хост может выбрать победителя.
    """
    try:
        return service.pick_winner(session_id, winner_session_movie_id, current_user.id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InvalidOperationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{session_id}/winner/by-participant", response_model=GameSessionResponse)
def pick_winner_by_participant(
    session_id: int,
    body: SelectWinnerParticipantRequest,
    current_user: Annotated[models.User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> GameSessionResponse:
    """Назначает победителя по user_id участника; фильм победителя становится итоговым."""
    try:
        return service.pick_winner_by_participant(
            session_id=session_id,
            winner_user_id=body.winner_user_id,
            current_user_id=current_user.id,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InvalidOperationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ───────────────────────── Участники ─────────────────────────


@router.post(
    "/{session_id}/participants",
    response_model=SessionParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
def join_session(
    session_id: int,
    current_user: Annotated[models.User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> SessionParticipantResponse:
    """Добавляет текущего пользователя как участника сессии."""
    try:
        return service.join_session(session_id, current_user.id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidOperationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AlreadyParticipantError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{session_id}/participants", status_code=status.HTTP_204_NO_CONTENT)
def leave_session(
    session_id: int,
    current_user: Annotated[models.User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> None:
    """Удаляет текущего пользователя из участников сессии."""
    try:
        service.leave_session(session_id, current_user.id)
    except ParticipantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/{session_id}/participants",
    response_model=list[SessionParticipantResponse],
)
def list_participants(
    session_id: int,
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
    _: Annotated[models.User, Depends(get_current_user)] = None,
) -> list[SessionParticipantResponse]:
    """Возвращает список участников сессии."""
    try:
        return service.list_participants(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ─────────────────── Фильмы в сессии ───────────────────────


@router.post(
    "/{session_id}/movies",
    response_model=SessionMovieResponse,
    status_code=status.HTTP_201_CREATED,
)
def propose_movie(
    session_id: int,
    movie_id: int,
    current_user: Annotated[models.User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> SessionMovieResponse:
    """
    Предлагает фильм в сессию от имени текущего пользователя.
    Пользователь должен быть участником сессии.
    """
    try:
        return service.propose_movie(session_id, movie_id, current_user.id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InvalidOperationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/{session_id}/movies/from-kinopoisk",
    response_model=SessionMovieResponse,
    status_code=status.HTTP_201_CREATED,
)
async def propose_movie_from_kinopoisk(
    session_id: int,
    body: AddMovieFromKinopoiskRequest,
    current_user: Annotated[models.User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> SessionMovieResponse:
    """
    Ищет точную карточку фильма по kinopoisk_id, кеширует фильм в локальной БД
    и добавляет его в игровую сессию.
    """
    try:
        return await service.propose_movie_from_kinopoisk(
            session_id=session_id,
            kinopoisk_id=body.kinopoisk_id,
            user_id=current_user.id,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{session_id}/movies/{session_movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def retract_movie(
    session_id: int,
    session_movie_id: int,
    current_user: Annotated[models.User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> None:
    """
    Убирает предложенный фильм из сессии.
    Удалить может только тот, кто предложил фильм, или хост сессии.
    """
    try:
        service.retract_movie(session_id, session_movie_id, current_user.id)
    except SessionMovieNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/{session_id}/movies",
    response_model=list[SessionMovieResponse],
)
def list_session_movies(
    session_id: int,
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
    _: Annotated[models.User, Depends(get_current_user)] = None,
) -> list[SessionMovieResponse]:
    """Возвращает все предложенные фильмы в сессии."""
    try:
        return service.list_session_movies(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{session_id}/selection",
    response_model=SessionParticipantResponse,
)
def select_movie(
    session_id: int,
    body: SelectParticipantMovieRequest,
    current_user: Annotated[models.User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> SessionParticipantResponse:
    """Сохраняет выбранный участником фильм в рамках игровой сессии."""
    try:
        return service.select_movie_for_participant(
            session_id=session_id,
            user_id=current_user.id,
            session_movie_id=body.session_movie_id,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InvalidOperationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
