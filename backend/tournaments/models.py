from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.models import Base


class TournamentRoomStatus(str, enum.Enum):
    LOBBY = "LOBBY"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"


class TournamentTestPreset(Base):
    __tablename__ = "tournament_test_presets"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False, unique=True)
    criteria_json = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())


class TournamentRoom(Base):
    __tablename__ = "tournament_rooms"

    id = Column(Integer, primary_key=True)
    invite_code = Column(String(12), nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    host_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    preset_id = Column(Integer, ForeignKey("tournament_test_presets.id"), nullable=True)
    bracket_size = Column(Integer, nullable=False)
    status = Column(SQLEnum(TournamentRoomStatus), nullable=False, default=TournamentRoomStatus.LOBBY)
    state_json = Column(Text, nullable=False)
    winner_movie_id = Column(Integer, ForeignKey("movies.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    preset = relationship("TournamentTestPreset")
    participants = relationship("TournamentParticipant", back_populates="room", cascade="all, delete-orphan")


class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"

    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("tournament_rooms.id"), nullable=False)
    user_key = Column(String(64), nullable=False)
    display_name = Column(String(64), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_host = Column(Boolean, nullable=False, default=False)
    joined_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())

    room = relationship("TournamentRoom", back_populates="participants")

    __table_args__ = (
        UniqueConstraint("room_id", "user_key", name="uq_tournament_participants_room_user_key"),
        Index("idx_tournament_participants_room", "room_id"),
    )


class TournamentVote(Base):
    __tablename__ = "tournament_votes"

    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("tournament_rooms.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("tournament_participants.id"), nullable=False)
    round_no = Column(Integer, nullable=False)
    match_no = Column(Integer, nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "participant_id",
            "round_no",
            "match_no",
            name="uq_tournament_votes_participant_round_match",
        ),
        Index("idx_tournament_votes_room_round_match", "room_id", "round_no", "match_no"),
    )
