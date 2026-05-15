from __future__ import annotations

import asyncio
import json
import secrets
from collections import Counter
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.exc import IntegrityError

from backend.database import SessionLocal
from backend.models import Movie
from backend.services.movie_service import MovieService
from backend.tournaments.bracket import (
    build_initial_pairs,
    normalize_bracket_size,
    progress_value,
    round_name,
    total_rounds,
)
from backend.tournaments.models import TournamentRoomStatus
from backend.tournaments.room_bus import RoomBus
from backend.tournaments.repository import TournamentRepository
from backend.tournaments.schemas import (
    TournamentCriteria,
    TournamentMatchState,
    TournamentMovieCard,
    TournamentParticipantOut,
    TournamentRoomState,
)


class TournamentService:
    def __init__(self, bus: RoomBus) -> None:
        self.bus = bus

    async def _safe_publish(self, room_key: str, payload: dict[str, Any]) -> None:
        try:
            await self.bus.publish(room_key, payload)
        except Exception:
            # Event bus sync must never block DB-authoritative room progression.
            return

    async def create_preset(self, name: str, criteria: TournamentCriteria) -> dict:
        return await asyncio.to_thread(self._create_preset_sync, name, criteria.model_dump())

    async def import_movies_from_kinopoisk(self, query: str, limit: int) -> dict:
        if not query.strip():
            raise ValueError("query must not be empty")

        db = SessionLocal()
        try:
            movie_service = MovieService(db)
            try:
                results = await movie_service.search_movies(query, limit=limit)
            except httpx.TimeoutException as exc:
                raise ValueError("Kinopoisk API timeout. Retry in a few seconds.") from exc
            except httpx.HTTPError as exc:
                raise ValueError(f"Kinopoisk API error: {exc}") from exc
            imported = 0
            for item in results:
                await movie_service.get_or_create_movie_by_kinopoisk_id(item.kinopoisk_id)
                imported += 1
            return {"imported": imported, "query": query, "limit": limit}
        finally:
            db.close()

    async def seed_demo_movies(self, target_count: int = 16) -> dict:
        return await asyncio.to_thread(self._seed_demo_movies_sync, target_count)

    def _seed_demo_movies_sync(self, target_count: int) -> dict:
        if target_count < 2:
            raise ValueError("target_count must be at least 2")

        db = SessionLocal()
        try:
            existing = db.query(Movie).count()
            if existing >= target_count:
                return {"created": 0, "total": existing}

            need = target_count - existing

            # Try to fetch real movies from Kinopoisk API using synchronous client
            try:
                from backend.services.kinopoisk_client import KinopoiskClient
                
                client = KinopoiskClient()
                movies_data = client.search_popular_russian_movies_sync(limit=need)

                if movies_data:
                    movie_service = MovieService(db)
                    added = 0
                    for movie_data in movies_data:
                        try:
                            if isinstance(movie_data, dict) and "id" in movie_data:
                                kp_id = movie_data["id"]
                                # Check if already exists
                                existing_movie = db.query(Movie).filter(
                                    Movie.kinopoisk_id == kp_id
                                ).first()
                                if not existing_movie:
                                    # Parse rating - it might be nested in a dict
                                    rating_val = movie_data.get("rating", 7.0)
                                    if isinstance(rating_val, dict):
                                        rating_val = rating_val.get("kp", 7.0)
                                    try:
                                        rating = float(rating_val) if rating_val else 7.0
                                    except (ValueError, TypeError):
                                        rating = 7.0
                                    
                                    movie = Movie(
                                        kinopoisk_id=kp_id,
                                        title=movie_data.get("name", f"Movie {kp_id}"),
                                        short_description=movie_data.get("description", ""),
                                        description=movie_data.get("description", ""),
                                        poster_url=movie_data.get("poster", {}).get("url", "") if isinstance(movie_data.get("poster"), dict) else "",
                                        year=movie_data.get("year", 2000),
                                        runtime=movie_data.get("movieLength", 90),
                                        rating=rating,
                                        cached_at=datetime.now(timezone.utc),
                                    )
                                    db.add(movie)
                                    added += 1
                        except Exception as e:
                            import logging
                            logging.warning(f"Failed to add movie {movie_data.get('id')}: {e}")
                            continue

                    if added > 0:
                        db.commit()
                        total = db.query(Movie).count()
                        return {"created": added, "total": total, "source": "kinopoisk"}

            except Exception as e:
                import logging
                logging.warning(f"Failed to fetch from Kinopoisk API: {e}. Falling back to test data.")

            # Fallback: create test movies if API fails
            max_kp = db.query(Movie.kinopoisk_id).order_by(Movie.kinopoisk_id.desc()).limit(1).scalar()
            base = int(max_kp or 990000) + 1

            for idx in range(need):
                kp = base + idx
                db.add(
                    Movie(
                        kinopoisk_id=kp,
                        title=f"Test Movie {kp}",
                        short_description="Test placeholder movie.",
                        description="Test placeholder movie.",
                        poster_url="https://placehold.co/400x600",
                        year=2000 + (idx % 25),
                        runtime=90 + (idx % 40),
                        rating=6.0 + ((idx % 35) / 10),
                        cached_at=datetime.now(timezone.utc),
                    )
                )

            db.commit()
            total = db.query(Movie).count()
            return {"created": need, "total": total, "source": "fallback"}
        finally:
            db.close()

    def _create_preset_sync(self, name: str, criteria: dict[str, Any]) -> dict:
        db = SessionLocal()
        try:
            repo = TournamentRepository(db)
            preset = repo.create_preset(name, criteria)
            return {"id": preset.id, "name": preset.name, "criteria": criteria}
        finally:
            db.close()

    async def list_presets(self) -> list[dict]:
        return await asyncio.to_thread(self._list_presets_sync)

    def _list_presets_sync(self) -> list[dict]:
        db = SessionLocal()
        try:
            repo = TournamentRepository(db)
            presets = repo.list_presets()
            return [
                {
                    "id": preset.id,
                    "name": preset.name,
                    "criteria": json.loads(preset.criteria_json),
                }
                for preset in presets
            ]
        finally:
            db.close()

    async def create_room(
        self,
        title: str,
        display_name: str,
        bracket_size: int,
        preset_id: int | None,
        criteria: TournamentCriteria | None,
        host_user_id: int | None,
        session_movie_ids: list[int] | None = None,
    ) -> tuple[int, str, TournamentRoomState]:
        return await asyncio.to_thread(
            self._create_room_sync,
            title,
            display_name,
            bracket_size,
            preset_id,
            criteria.model_dump() if criteria else None,
            host_user_id,
            session_movie_ids,
        )

    def _create_room_sync(
        self,
        title: str,
        display_name: str,
        bracket_size: int,
        preset_id: int | None,
        criteria: dict[str, Any] | None,
        host_user_id: int | None,
        session_movie_ids: list[int] | None = None,
    ) -> tuple[int, str, TournamentRoomState]:
        db = SessionLocal()
        try:
            repo = TournamentRepository(db)
            selected_criteria = criteria or {}
            if preset_id is not None:
                preset = repo.get_preset(preset_id)
                if preset is None:
                    raise ValueError("Preset not found")
                selected_criteria = json.loads(preset.criteria_json)

            # Bug 2 fix: prefer explicit session movies picked by players.
            # The old path fell back to `get_movies_by_criteria` / `get_random_movies`
            # which produced a bracket completely unrelated to the session's
            # SessionMovie records. When the caller provides `session_movie_ids`
            # we build the bracket from exactly those movies.
            if session_movie_ids:
                unique_ids = list(dict.fromkeys(session_movie_ids))
                movies = repo.get_movies_by_ids(unique_ids)
                if len(movies) < 2:
                    raise ValueError(
                        "Need at least 2 session movies to build a MovieCO bracket"
                    )
                # Keep only movies whose ids were actually requested, drop any
                # leftovers that the DB might have returned in unexpected order.
                movie_by_id = {m.id: m for m in movies}
                ordered = [movie_by_id[mid] for mid in unique_ids if mid in movie_by_id]
                size = normalize_bracket_size(len(ordered))
                if len(ordered) < size:
                    # Pad the bracket with duplicates so it always fills a
                    # power-of-two bracket. This keeps the invariant that
                    # every id in the bracket comes from the session.
                    while len(ordered) < size:
                        ordered.append(ordered[len(ordered) % len(movies)])
                movies = ordered[:size]
            else:
                size = normalize_bracket_size(bracket_size)
                movies = repo.get_movies_by_criteria(selected_criteria, size)
                if len(movies) < size:
                    fallback = repo.get_random_movies(size)
                    movie_by_id = {movie.id: movie for movie in movies}
                    for movie in fallback:
                        movie_by_id[movie.id] = movie
                    movies = list(movie_by_id.values())

                if len(movies) < size:
                    raise ValueError("Not enough cached movies in DB for bracket size")

            pairs = build_initial_pairs([movie.id for movie in movies], size)
            rounds = [pairs]
            pairs_count = len(pairs)
            while pairs_count > 1:
                pairs_count //= 2
                rounds.append([[None, None] for _ in range(pairs_count)])

            state = {
                "round_no": 1,
                "match_no": 1,
                "total_rounds": total_rounds(size),
                "rounds": rounds,
                "criteria": selected_criteria,
                "winner_movie_id": None,
            }
            room = repo.create_room(
                title=title,
                host_user_id=host_user_id,
                preset_id=preset_id,
                bracket_size=size,
                state=state,
            )
            user_key = secrets.token_urlsafe(18)
            repo.add_participant(
                room_id=room.id,
                user_key=user_key,
                display_name=display_name,
                user_id=host_user_id,
                is_host=True,
            )
            room_state = self._build_room_state(repo, room)
            return room.id, user_key, room_state
        finally:
            db.close()

    async def join_room(self, room_id: int, display_name: str, user_id: int | None) -> tuple[str, TournamentRoomState]:
        return await asyncio.to_thread(self._join_room_sync, room_id, display_name, user_id)

    def _join_room_sync(self, room_id: int, display_name: str, user_id: int | None) -> tuple[str, TournamentRoomState]:
        db = SessionLocal()
        try:
            repo = TournamentRepository(db)
            room = repo.get_room_by_id(room_id)
            if room is None:
                raise ValueError("Room not found")

            # Idempotent join: if a participant with the same display_name
            # already exists, return their existing user_key instead of
            # creating a duplicate (which would be non-host and break start_room).
            existing_participants = repo.list_participants(room.id)
            for p in existing_participants:
                if p.display_name == display_name:
                    room_state = self._build_room_state(repo, room)
                    return p.user_key, room_state

            user_key = secrets.token_urlsafe(18)
            repo.add_participant(
                room_id=room.id,
                user_key=user_key,
                display_name=display_name,
                user_id=user_id,
                is_host=False,
            )
            room_state = self._build_room_state(repo, room)
            return user_key, room_state
        finally:
            db.close()

    async def get_room_state(self, room_id: int) -> TournamentRoomState:
        return await asyncio.to_thread(self._get_room_state_sync, room_id)

    def _get_room_state_sync(self, room_id: int) -> TournamentRoomState:
        db = SessionLocal()
        try:
            repo = TournamentRepository(db)
            room = repo.get_room_by_id(room_id)
            if room is None:
                raise ValueError("Room not found")
            return self._build_room_state(repo, room)
        finally:
            db.close()

    async def start_room(self, room_id: int, user_key: str) -> TournamentRoomState:
        state = await asyncio.to_thread(self._start_room_sync, room_id, user_key)
        await self._safe_publish(str(room_id), {"type": "room_state", "payload": state.model_dump()})
        return state

    def _start_room_sync(self, room_id: int, user_key: str) -> TournamentRoomState:
        db = SessionLocal()
        try:
            repo = TournamentRepository(db)
            room = repo.get_room_by_id(room_id)
            if room is None:
                raise ValueError("Room not found")
            participant = repo.get_participant_by_key(room.id, user_key)
            if participant is None:
                raise ValueError("Participant not found")
            if not participant.is_host:
                raise PermissionError("Only host can start tournament")
            repo.set_room_status(room, TournamentRoomStatus.RUNNING)
            return self._build_room_state(repo, room)
        finally:
            db.close()

    async def submit_vote(self, room_id: int, user_key: str, movie_id: int) -> TournamentRoomState:
        state = await asyncio.to_thread(self._submit_vote_sync, room_id, user_key, movie_id)
        await self._safe_publish(str(room_id), {"type": "room_state", "payload": state.model_dump()})
        return state

    def _submit_vote_sync(self, room_id: int, user_key: str, movie_id: int) -> TournamentRoomState:
        db = SessionLocal()
        try:
            repo = TournamentRepository(db)
            room = repo.get_room_by_id(room_id)
            if room is None:
                raise ValueError("Room not found")
            if room.status != TournamentRoomStatus.RUNNING:
                raise ValueError("Tournament is not running")

            participant = repo.get_participant_by_key(room.id, user_key)
            if participant is None:
                raise ValueError("Participant not found")

            state = json.loads(room.state_json)
            round_no = state["round_no"]
            match_no = state["match_no"]
            pair = state["rounds"][round_no - 1][match_no - 1]
            if movie_id not in pair:
                raise ValueError("Movie is not in the active pair")

            # idempotent insert guard
            existing_votes = repo.list_votes(room.id, round_no, match_no)
            if any(v.participant_id == participant.id for v in existing_votes):
                return self._build_room_state(repo, room)

            try:
                repo.add_vote(room.id, participant.id, round_no, match_no, movie_id)
            except IntegrityError:
                db.rollback()
                return self._build_room_state(repo, room)

            all_participants = repo.list_participants(room.id)
            votes = repo.list_votes(room.id, round_no, match_no)
            if len(votes) >= len(all_participants):
                self._close_match(state, votes, room.bracket_size)
                repo.update_state(room, state)
                if state.get("winner_movie_id") is not None:
                    room.winner_movie_id = state["winner_movie_id"]
                    room.status = TournamentRoomStatus.FINISHED
                    db.add(room)
                    db.commit()
                    db.refresh(room)
                    # Bug: finished MovieCO tournament wasn't surfaced on
                    # the /result page and "история игр" because only
                    # TournamentRoom was being updated — the underlying
                    # GameSession stayed in PLAYING with no winner set.
                    # Sync the winner over to the GameSession so the
                    # result page and profile history pick it up.
                    self._sync_movieco_winner_to_game_session(
                        db,
                        tournament_title=room.title,
                        winner_movie_id=state["winner_movie_id"],
                    )

            return self._build_room_state(repo, room)
        finally:
            db.close()

    async def list_rooms(self, limit: int = 20, only_lobby: bool = True) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_rooms_sync, limit, only_lobby)

    def _list_rooms_sync(self, limit: int, only_lobby: bool) -> list[dict[str, Any]]:
        db = SessionLocal()
        try:
            repo = TournamentRepository(db)
            rooms = repo.list_rooms(limit=limit, only_lobby=only_lobby)
            result: list[dict[str, Any]] = []
            for room in rooms:
                result.append(
                    {
                        "room_id": room.id,
                        "title": room.title,
                        "status": room.status,
                        "participants": repo.count_participants(room.id),
                        "bracket_size": room.bracket_size,
                    }
                )
            return result
        finally:
            db.close()

    def _close_match(self, state: dict[str, Any], votes: list[Any], bracket_size: int) -> None:
        round_no = state["round_no"]
        match_no = state["match_no"]
        rounds = state["rounds"]
        current_pair = rounds[round_no - 1][match_no - 1]

        counter = Counter(v.movie_id for v in votes)
        if not counter:
            winner = current_pair[0]
        else:
            most_common = counter.most_common()
            if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
                winner = secrets.choice(current_pair)
            else:
                winner = most_common[0][0]

        if round_no >= state["total_rounds"]:
            state["winner_movie_id"] = winner
            return

        next_round = round_no + 1
        target_match = ((match_no - 1) // 2) + 1
        slot = 0 if (match_no - 1) % 2 == 0 else 1
        rounds[next_round - 1][target_match - 1][slot] = winner

        matches_in_round = len(rounds[round_no - 1])
        if match_no < matches_in_round:
            state["match_no"] = match_no + 1
            return

        state["round_no"] = next_round
        state["match_no"] = 1

    def _build_room_state(self, repo: TournamentRepository, room) -> TournamentRoomState:
        state = json.loads(room.state_json)
        participants = repo.list_participants(room.id)

        participant_items = [
            TournamentParticipantOut(
                id=p.id,
                user_key=p.user_key,
                display_name=p.display_name,
                is_host=p.is_host,
            )
            for p in participants
        ]

        movie_map = {}
        current_match = None
        winner = None

        if room.status != TournamentRoomStatus.FINISHED:
            round_no = state["round_no"]
            match_no = state["match_no"]
            pair = state["rounds"][round_no - 1][match_no - 1]
            movie_ids = [mid for mid in pair if mid is not None]
            for movie in repo.get_movies_by_ids(movie_ids):
                movie_map[movie.id] = movie
            if len(movie_ids) == 2 and all(mid in movie_map for mid in movie_ids):
                current_match = TournamentMatchState(
                    round_no=round_no,
                    match_no=match_no,
                    left=self._movie_card(movie_map[movie_ids[0]]),
                    right=self._movie_card(movie_map[movie_ids[1]]),
                )
        else:
            winner_id = state.get("winner_movie_id")
            if winner_id is not None:
                winner_movies = repo.get_movies_by_ids([winner_id])
                if winner_movies:
                    winner = self._movie_card(winner_movies[0])

        round_no = state.get("round_no", 1)
        total = state.get("total_rounds", 1)
        match_no = state.get("match_no", 1)

        return TournamentRoomState(
            room_id=room.id,
            title=room.title,
            status=room.status,
            bracket_size=room.bracket_size,
            round_name=round_name(round_no, total),
            progress=progress_value(round_no, match_no, room.bracket_size),
            participants=participant_items,
            current_match=current_match,
            winner=winner,
        )

    def _movie_card(self, movie: Movie) -> TournamentMovieCard:
        return TournamentMovieCard(
            movie_id=movie.id,
            kinopoisk_id=movie.kinopoisk_id,
            title=movie.title,
            poster_url=movie.poster_url,
            year=movie.year,
            rating=movie.rating,
        )

    def _sync_movieco_winner_to_game_session(
        self,
        db,
        *,
        tournament_title: str,
        winner_movie_id: int,
    ) -> None:
        """
        MovieCO tournament lives in its own tables (`tournament_*`), but
        the shared `/result` page and the user's game history read from
        `GameSession.winner_session_movie_id`. When the bracket finishes
        we link the two: resolve the GameSession via the tournament
        title ("Session {invite_code}"), find the SessionMovie for the
        winning movie_id, and mark the game session as FINISHED with
        the right winner. Best-effort — failure here must not roll back
        the tournament write.
        """
        import logging  # noqa: PLC0415

        from backend.crud.game_session import (  # noqa: PLC0415
            get_game_session_by_invite_code,
            set_winner,
        )
        from backend.crud.session_movie import get_movies_by_session  # noqa: PLC0415
        from backend.models import SessionStatus  # noqa: PLC0415

        logger = logging.getLogger(__name__)

        prefix = "Session "
        if not tournament_title.startswith(prefix):
            return
        invite_code = tournament_title[len(prefix):].strip()
        if not invite_code:
            return

        try:
            game_session = get_game_session_by_invite_code(db, invite_code)
            if game_session is None:
                logger.warning(
                    "MovieCO winner sync: no GameSession for invite_code=%s",
                    invite_code,
                )
                return

            session_movies = get_movies_by_session(db, game_session.id)
            winning = next(
                (sm for sm in session_movies if sm.movie_id == winner_movie_id),
                None,
            )
            if winning is None:
                logger.warning(
                    "MovieCO winner sync: movie_id=%s not in session_movies for %s",
                    winner_movie_id,
                    invite_code,
                )
                # Still mark session finished so it shows up in history.
                if game_session.status != SessionStatus.FINISHED:
                    from backend.crud.game_session import update_session_status  # noqa: PLC0415
                    update_session_status(db, game_session, SessionStatus.FINISHED)
                return

            set_winner(db, game_session, winning.id)
            logger.info(
                "MovieCO winner synced to GameSession %s: session_movie_id=%s movie_id=%s",
                invite_code,
                winning.id,
                winner_movie_id,
            )
        except Exception:
            logger.exception(
                "MovieCO winner sync failed for %s; tournament state is still committed",
                invite_code,
            )
            try:
                db.rollback()
            except Exception:  # pragma: no cover - best-effort cleanup
                pass
