from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend import models
from backend.database import get_db
from backend.schemas.game_session import (
    GameSessionResponse,
    JoinSessionByCodeRequest,
    SessionMovieResponse,
    SessionParticipantResponse,
)
from backend.crud.game_session import (
    create_game_session,
    get_game_session_by_id,
    get_game_session_by_invite_code,
    get_sessions_by_user,
    update_session_status,
    set_winner,
)
from backend.crud.session_participant import (
    add_participant,
    remove_participant,
    get_participants_by_session,
    is_participant,
)
from backend.crud.session_movie import (
    add_movie_to_session,
    remove_movie_from_session,
    get_movies_by_session,
    get_session_movie_by_id,
)
from backend.models import SessionStatus
from backend.security import get_current_user

router = APIRouter(prefix="/sessions", tags=["game sessions"])


# ─────────────────── Вспомогательная зависимость ───────────────────


def get_session_or_404(session_id: int, db: Session = Depends(get_db)):
    """Возвращает игровую сессию или выбрасывает 404."""
    game_session = get_game_session_by_id(db, session_id)
    if not game_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Игровая сессия не найдена",
        )
    return game_session


# ─────────────────────── Игровые сессии ───────────────────────


@router.post(
    "/",
    response_model=GameSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> GameSessionResponse:
    """Создаёт новую игровую сессию. Текущий пользователь становится хостом."""
    return create_game_session(db, host_user_id=current_user.id)


@router.post(
    "/join-by-code",
    response_model=SessionParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
def join_session_by_code(
    body: JoinSessionByCodeRequest,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> SessionParticipantResponse:
    """Добавляет текущего пользователя в сессию по invite_code."""
    game_session = get_game_session_by_invite_code(db, body.invite_code)
    if not game_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Игровая сессия не найдена",
        )

    if is_participant(db, game_session.id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Вы уже являетесь участником этой сессии",
        )

    try:
        return add_participant(db, game_session.id, current_user.id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Вы уже являетесь участником этой сессии",
        )


@router.get("/my/list", response_model=list[GameSessionResponse])
def list_my_sessions(
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
) -> list[GameSessionResponse]:
    """Возвращает сессии, где текущий пользователь — хост."""
    return get_sessions_by_user(db, current_user.id, skip, limit)


@router.get("/{session_id}", response_model=GameSessionResponse)
def read_session(
    session_id: int,
    db: Session = Depends(get_db),
    _: Annotated[models.User, Depends(get_current_user)] = None,
) -> GameSessionResponse:
    """Возвращает данные игровой сессии по ID."""
    return get_session_or_404(session_id, db)


@router.post("/{session_id}/winner", response_model=GameSessionResponse)
def pick_winner(
    session_id: int,
    winner_session_movie_id: int,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> GameSessionResponse:
    """
    Назначает фильм-победитель и завершает сессию.
    Только хост может выбрать победителя.
    """
    game_session = get_session_or_404(session_id, db)

    if game_session.host_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только хост может выбрать победителя",
        )

    # Проверяем что фильм принадлежит этой сессии
    session_movie = get_session_movie_by_id(db, winner_session_movie_id)
    if not session_movie or session_movie.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Указанный фильм не принадлежит данной сессии",
        )

    return set_winner(db, game_session, winner_session_movie_id)


# ───────────────────────── Участники ─────────────────────────


@router.post(
    "/{session_id}/participants",
    response_model=SessionParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
def join_session(
    session_id: int,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> SessionParticipantResponse:
    """Добавляет текущего пользователя как участника сессии."""
    # Убедимся, что сессия существует
    get_session_or_404(session_id, db)

    if is_participant(db, session_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Вы уже являетесь участником этой сессии",
        )

    try:
        return add_participant(db, session_id, current_user.id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Вы уже являетесь участником этой сессии",
        )


@router.delete("/{session_id}/participants", status_code=status.HTTP_204_NO_CONTENT)
def leave_session(
    session_id: int,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> None:
    """Удаляет текущего пользователя из участников сессии."""
    removed = remove_participant(db, session_id, current_user.id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не являетесь участником этой сессии",
        )


@router.get(
    "/{session_id}/participants",
    response_model=list[SessionParticipantResponse],
)
def list_participants(
    session_id: int,
    db: Session = Depends(get_db),
    _: Annotated[models.User, Depends(get_current_user)] = None,
) -> list[SessionParticipantResponse]:
    """Возвращает список участников сессии."""
    get_session_or_404(session_id, db)
    return get_participants_by_session(db, session_id)


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
    db: Session = Depends(get_db),
) -> SessionMovieResponse:
    """
    Предлагает фильм в сессию от имени текущего пользователя.
    Пользователь должен быть участником сессии.
    """
    get_session_or_404(session_id, db)

    if not is_participant(db, session_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только участники сессии могут предлагать фильмы",
        )

    try:
        return add_movie_to_session(db, session_id, movie_id, current_user.id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Этот фильм уже предложен в данной сессии",
        )


@router.delete(
    "/{session_id}/movies/{session_movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def retract_movie(
    session_id: int,
    session_movie_id: int,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> None:
    """
    Убирает предложенный фильм из сессии.
    Удалить может только тот, кто предложил фильм, или хост сессии.
    """
    session_movie = get_session_movie_by_id(db, session_movie_id)
    if not session_movie or session_movie.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фильм не найден в этой сессии",
        )

    game_session = get_session_or_404(session_id, db)

    # Удалить может автор предложения или хост сессии
    if (
        session_movie.proposed_by_user_id != current_user.id
        and game_session.host_user_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на удаление этого фильма из сессии",
        )

    remove_movie_from_session(db, session_movie_id)


@router.get(
    "/{session_id}/movies",
    response_model=list[SessionMovieResponse],
)
def list_session_movies(
    session_id: int,
    db: Session = Depends(get_db),
    _: Annotated[models.User, Depends(get_current_user)] = None,
) -> list[SessionMovieResponse]:
    """Возвращает все предложенные фильмы в сессии."""
    get_session_or_404(session_id, db)
    return get_movies_by_session(db, session_id)
