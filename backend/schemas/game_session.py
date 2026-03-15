from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.models import SessionStatus


class GameSessionResponse(BaseModel):
    """Schema ответа с данными игровой сессии."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    host_user_id: int
    status: SessionStatus
    winner_session_movie_id: int | None = None
    started_at: datetime
    finished_at: datetime | None = None


class SessionParticipantResponse(BaseModel):
    """Schema ответа с данными участника сессии."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    session_id: int


class SessionMovieResponse(BaseModel):
    """Schema ответа с данными фильма, предложенного в сессии."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    movie_id: int
    proposed_by_user_id: int
