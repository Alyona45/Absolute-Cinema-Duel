from __future__ import annotations

import json
import random
import string
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from backend.models import Genre, Movie, MovieGenre
from backend.tournaments.models import (
    TournamentParticipant,
    TournamentRoom,
    TournamentRoomStatus,
    TournamentTestPreset,
    TournamentVote,
)


class TournamentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_preset(self, name: str, criteria: dict[str, Any]) -> TournamentTestPreset:
        preset = TournamentTestPreset(name=name, criteria_json=json.dumps(criteria))
        self.db.add(preset)
        self.db.commit()
        self.db.refresh(preset)
        return preset

    def list_presets(self) -> list[TournamentTestPreset]:
        return self.db.execute(select(TournamentTestPreset).order_by(TournamentTestPreset.id.desc())).scalars().all()

    def get_preset(self, preset_id: int) -> TournamentTestPreset | None:
        return self.db.get(TournamentTestPreset, preset_id)

    def get_movies_by_criteria(self, criteria: dict[str, Any], limit: int) -> list[Movie]:
        stmt = select(Movie)
        genres = criteria.get("genres") or []
        if genres:
            stmt = stmt.join(MovieGenre, MovieGenre.movie_id == Movie.id).join(Genre, Genre.id == MovieGenre.genre_id)
            stmt = stmt.where(Genre.name.in_(genres))

        year_from = criteria.get("year_from")
        year_to = criteria.get("year_to")
        rating_from = criteria.get("rating_from")
        rating_to = criteria.get("rating_to")
        title_contains = criteria.get("title_contains")

        conditions = []
        if year_from is not None:
            conditions.append(Movie.year >= year_from)
        if year_to is not None:
            conditions.append(Movie.year <= year_to)
        if rating_from is not None:
            conditions.append(Movie.rating >= rating_from)
        if rating_to is not None:
            conditions.append(Movie.rating <= rating_to)
        if title_contains:
            conditions.append(Movie.title.ilike(f"%{title_contains}%"))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.group_by(Movie.id).order_by(func.random()).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def get_random_movies(self, limit: int) -> list[Movie]:
        stmt = select(Movie).order_by(func.random()).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def get_movies_by_ids(self, ids: list[int]) -> list[Movie]:
        if not ids:
            return []
        stmt = select(Movie).where(Movie.id.in_(ids))
        return self.db.execute(stmt).scalars().all()

    def create_room(
        self,
        title: str,
        host_user_id: int | None,
        preset_id: int | None,
        bracket_size: int,
        state: dict[str, Any],
    ) -> TournamentRoom:
        invite_code = self._generate_invite_code()
        room = TournamentRoom(
            invite_code=invite_code,
            title=title,
            host_user_id=host_user_id,
            preset_id=preset_id,
            bracket_size=bracket_size,
            status=TournamentRoomStatus.LOBBY,
            state_json=json.dumps(state),
        )
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

    def add_participant(
        self,
        room_id: int,
        user_key: str,
        display_name: str,
        user_id: int | None,
        is_host: bool,
    ) -> TournamentParticipant:
        participant = TournamentParticipant(
            room_id=room_id,
            user_key=user_key,
            display_name=display_name,
            user_id=user_id,
            is_host=is_host,
        )
        self.db.add(participant)
        self.db.commit()
        self.db.refresh(participant)
        return participant

    def get_room_by_invite_code(self, invite_code: str) -> TournamentRoom | None:
        stmt = select(TournamentRoom).where(TournamentRoom.invite_code == invite_code)
        return self.db.execute(stmt).scalars().first()

    def get_room_by_id(self, room_id: int) -> TournamentRoom | None:
        return self.db.get(TournamentRoom, room_id)

    def list_rooms(self, limit: int = 20, only_lobby: bool = False) -> list[TournamentRoom]:
        stmt = select(TournamentRoom)
        if only_lobby:
            stmt = stmt.where(TournamentRoom.status == TournamentRoomStatus.LOBBY)
        stmt = stmt.order_by(TournamentRoom.created_at.desc()).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def list_participants(self, room_id: int) -> list[TournamentParticipant]:
        stmt = select(TournamentParticipant).where(TournamentParticipant.room_id == room_id).order_by(TournamentParticipant.id)
        return self.db.execute(stmt).scalars().all()

    def count_participants(self, room_id: int) -> int:
        stmt = select(func.count(TournamentParticipant.id)).where(TournamentParticipant.room_id == room_id)
        value = self.db.execute(stmt).scalar_one()
        return int(value)

    def get_participant_by_key(self, room_id: int, user_key: str) -> TournamentParticipant | None:
        stmt = select(TournamentParticipant).where(
            TournamentParticipant.room_id == room_id,
            TournamentParticipant.user_key == user_key,
        )
        return self.db.execute(stmt).scalars().first()

    def set_room_status(self, room: TournamentRoom, status: TournamentRoomStatus) -> TournamentRoom:
        room.status = status
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

    def update_state(self, room: TournamentRoom, state: dict[str, Any]) -> TournamentRoom:
        room.state_json = json.dumps(state)
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

    def add_vote(
        self,
        room_id: int,
        participant_id: int,
        round_no: int,
        match_no: int,
        movie_id: int,
    ) -> TournamentVote:
        vote = TournamentVote(
            room_id=room_id,
            participant_id=participant_id,
            round_no=round_no,
            match_no=match_no,
            movie_id=movie_id,
        )
        self.db.add(vote)
        self.db.commit()
        self.db.refresh(vote)
        return vote

    def list_votes(self, room_id: int, round_no: int, match_no: int) -> list[TournamentVote]:
        stmt = select(TournamentVote).where(
            TournamentVote.room_id == room_id,
            TournamentVote.round_no == round_no,
            TournamentVote.match_no == match_no,
        )
        return self.db.execute(stmt).scalars().all()

    def _generate_invite_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(random.choice(alphabet) for _ in range(6))
            exists = self.get_room_by_invite_code(code)
            if not exists:
                return code
