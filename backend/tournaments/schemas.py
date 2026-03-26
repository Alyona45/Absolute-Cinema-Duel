from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.tournaments.models import TournamentRoomStatus


class TournamentCriteria(BaseModel):
    genres: list[str] = Field(default_factory=list)
    year_from: int | None = None
    year_to: int | None = None
    rating_from: float | None = None
    rating_to: float | None = None
    title_contains: str | None = None


class TournamentTestPresetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    criteria: TournamentCriteria


class TournamentTestPresetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    criteria: TournamentCriteria


class TournamentRoomCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    display_name: str = Field(min_length=1, max_length=64)
    bracket_size: int = Field(default=16, ge=2, le=16)
    preset_id: int | None = None
    criteria: TournamentCriteria | None = None


class TournamentJoinRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=64)


class TournamentParticipantOut(BaseModel):
    id: int
    user_key: str
    display_name: str
    is_host: bool


class TournamentMovieCard(BaseModel):
    movie_id: int
    kinopoisk_id: int
    title: str
    poster_url: str | None = None
    year: int | None = None
    rating: float | None = None


class TournamentMatchState(BaseModel):
    round_no: int
    match_no: int
    left: TournamentMovieCard
    right: TournamentMovieCard


class TournamentRoomState(BaseModel):
    room_id: int
    title: str
    status: TournamentRoomStatus
    bracket_size: int
    round_name: str
    progress: float
    participants: list[TournamentParticipantOut]
    current_match: TournamentMatchState | None = None
    winner: TournamentMovieCard | None = None


class TournamentRoomCreated(BaseModel):
    room_id: int
    user_key: str
    room: TournamentRoomState


class TournamentJoinedResponse(BaseModel):
    room_id: int
    user_key: str
    room: TournamentRoomState


class WsVoteEvent(BaseModel):
    type: Literal["vote"]
    movie_id: int


class WsPingEvent(BaseModel):
    type: Literal["ping"]


class WsEnvelope(BaseModel):
    type: str
    payload: dict
