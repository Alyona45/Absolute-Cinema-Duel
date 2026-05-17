from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.models import SessionStatus
from backend.schemas.movie import MovieResponse


class GameSessionResponse(BaseModel):
    """Schema ответа с данными игровой сессии."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    host_user_id: int | None
    invite_code: str
    status: SessionStatus
    winner_session_movie_id: int | None = None
    winner_movie_id: int | None = None
    winner_user_id: int | None = None
    winner_session_movie: SessionMovieResponse | None = None
    started_at: datetime
    finished_at: datetime | None = None


class JoinSessionByCodeRequest(BaseModel):
    """Schema запроса для входа в игровую сессию по invite_code."""

    invite_code: str


class SessionParticipantResponse(BaseModel):
    """Schema ответа с данными участника сессии."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    guest_id: str | None
    session_id: int
    display_name: str
    is_host: bool
    selected_session_movie_id: int | None = None


class SelectParticipantMovieRequest(BaseModel):
    """Schema запроса для выбора фильма участником в рамках сессии."""

    session_movie_id: int


class SelectWinnerParticipantRequest(BaseModel):
    """Schema запроса для выбора победителя по participant_id участника сессии."""

    winner_participant_id: int


class SessionMovieResponse(BaseModel):
    """Schema ответа с данными фильма, предложенного в сессии."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    movie_id: int
    proposed_by_participant_id: int
    movie: MovieResponse | None = None
