import logging

from sqlalchemy.orm import Session

from backend.actors import CurrentActor, runtime_user_id_for_actor, runtime_user_id_for_participant
from backend.crud.game_session import get_game_session_by_invite_code
from backend.crud.session_participant import (
    get_host_participant,
    get_participant_by_actor,
    get_participants_by_session,
    is_participant,
)
from backend.models import SessionStatus
from backend.services.errors import (
    AccessDeniedError,
    AlreadyParticipantError,
    InvalidOperationError,
    SessionNotFoundError,
)
from backend.services.game_session_service import GameSessionService
from backend.websocket.manager import ConnectionManager
from backend.websocket.models import Participant, Room
from backend.websocket.room import RoomManager

logger = logging.getLogger(__name__)


class WsRoomService:
    def __init__(
        self,
        db: Session,
        room_manager: RoomManager,
        connection_manager: ConnectionManager,
    ) -> None:
        self.db = db
        self.room_manager = room_manager
        self.connection_manager = connection_manager
        self.game_session_service = GameSessionService(db)

    def create_room(self, actor: CurrentActor) -> dict[str, str]:
        game_session = self.game_session_service.create_session(host_actor=actor)
        runtime_user_id = runtime_user_id_for_actor(actor)
        room_id, user_id = self.room_manager.create_room(
            host_username=actor.display_name,
            is_guest=actor.is_guest,
            email=actor.email,
            room_id=game_session.invite_code,
            user_id=runtime_user_id,
        )
        return {"room_id": room_id, "user_id": user_id, "username": actor.display_name}

    def join_room(self, room_id: str, actor: CurrentActor) -> dict[str, str]:
        try:
            participant = self.game_session_service.join_by_invite_code(room_id, actor)
        except AlreadyParticipantError:
            game_session = get_game_session_by_invite_code(self.db, room_id)
            if game_session is None:
                raise SessionNotFoundError("Комната не найдена или игра уже началась")
            participant = get_participant_by_actor(self.db, game_session.id, actor)
            if participant is None:
                raise

        room = self.ensure_runtime_room(room_id)
        if room is None:
            raise SessionNotFoundError("Комната не найдена или игра уже началась")

        user_id = self.room_manager.join_room(
            room_id=room_id,
            username=participant.display_name,
            is_guest=participant.user_id is None,
            email=participant.user.email if participant.user is not None else None,
            user_id=runtime_user_id_for_participant(participant),
        )
        if user_id is None:
            raise InvalidOperationError("Комната не найдена или игра уже началась")

        return {"user_id": user_id, "username": participant.display_name}

    async def start_room(
        self,
        room_id: str,
        actor: CurrentActor,
    ) -> dict[str, str]:
        room = self.ensure_runtime_room(room_id)
        if room is None:
            raise SessionNotFoundError("Комната не найдена")

        self.game_session_service.start_session_by_invite_code(room_id, actor)

        ok = self.room_manager.start_game(room_id)
        if not ok:
            raise InvalidOperationError("Невозможно начать игру (неверный статус комнаты)")

        participants = self.room_manager.participant_ids(room_id)
        from backend.websocket.protocol import serialize_game_started

        results = await self.connection_manager.broadcast(participants, serialize_game_started(room_id))
        failed = [uid for uid, success in results.items() if not success]
        if failed:
            logger.error("Не удалось отправить GAME_STARTED %s пользователям: %s", len(failed), failed)
            raise InvalidOperationError("Игра запущена, но не все участники получили уведомление")
        return {"status": "ok"}

    def get_room(self, room_id: str) -> dict:
        room = self.ensure_runtime_room(room_id)
        if room is None:
            raise SessionNotFoundError("Комната не найдена")
        return room.to_dict()

    def ensure_runtime_room(self, room_id: str) -> Room | None:
        room = self.room_manager.get_room(room_id)
        if room is not None:
            return room
        return self._rebuild_runtime_room(room_id)

    def validate_db_membership(
        self,
        room_id: str,
        user_id: str,
        participant: Participant,
    ) -> bool:
        game_session = get_game_session_by_invite_code(self.db, room_id)
        if game_session is None:
            return False

        if participant.is_guest:
            guest_id = user_id.removeprefix("guest:")
            return is_participant(self.db, game_session.id, guest_id=guest_id)

        if participant.email is None:
            return False

        db_participants = get_participants_by_session(self.db, game_session.id)
        return any(
            db_participant.user is not None
            and db_participant.user.email == participant.email
            and str(db_participant.user_id) == user_id
            for db_participant in db_participants
        )

    def _rebuild_runtime_room(self, invite_code: str) -> Room | None:
        game_session = get_game_session_by_invite_code(self.db, invite_code)
        if game_session is None:
            return None

        host_participant = get_host_participant(self.db, game_session.id)
        if host_participant is None:
            return None

        try:
            self.room_manager.create_room(
                host_username=host_participant.display_name,
                is_guest=host_participant.user_id is None,
                email=host_participant.user.email if host_participant.user is not None else None,
                room_id=invite_code,
                user_id=runtime_user_id_for_participant(host_participant),
            )
        except ValueError:
            existing_room = self.room_manager.get_room(invite_code)
            if existing_room is not None:
                return existing_room
            raise

        room = self.room_manager.get_room(invite_code)
        if room is None:
            return None

        participants = get_participants_by_session(self.db, game_session.id)
        for participant in participants:
            participant_id = runtime_user_id_for_participant(participant)
            if participant_id in room.participants:
                continue

            if participant.user_id is None:
                room.add_participant(
                    participant_id,
                    Participant.guest(username=participant.display_name),
                )
            else:
                room.add_participant(
                    participant_id,
                    Participant.authenticated(
                        username=participant.display_name,
                        email=participant.user.email,
                    ),
                )

        if game_session.status == SessionStatus.PLAYING:
            self.room_manager.start_game(invite_code)
        elif game_session.status in (SessionStatus.FINISHED, SessionStatus.CANCELLED):
            self.room_manager.finish_game(invite_code)

        return room
