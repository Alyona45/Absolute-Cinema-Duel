import logging
import uuid

from sqlalchemy.orm import Session

from backend import models
from backend.crud.game_session import get_game_session_by_invite_code
from backend.crud.session_participant import is_participant
from backend.crud.user import get_user_by_email
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

    @staticmethod
    def guest_username(name: str | None) -> str:
        if name:
            return name
        return f"Гость_{uuid.uuid4().hex[:6]}"

    def create_room(
        self,
        current_user: models.User | None,
        username: str | None,
    ) -> dict[str, str]:
        if current_user is None:
            resolved_name = self.guest_username(username)
            room_id, user_id = self.room_manager.create_room(resolved_name, is_guest=True)
            return {"room_id": room_id, "user_id": user_id, "username": resolved_name}

        resolved_name = current_user.username or current_user.email
        game_session = self.game_session_service.create_session(host_user_id=current_user.id)
        room_id, user_id = self.room_manager.create_room(
            host_username=resolved_name,
            is_guest=False,
            email=current_user.email,
            room_id=game_session.invite_code,
            user_id=str(current_user.id),
        )
        return {"room_id": room_id, "user_id": user_id}

    def join_room(
        self,
        room_id: str,
        current_user: models.User | None,
        username: str | None,
    ) -> dict[str, str]:
        if current_user is None:
            game_session = get_game_session_by_invite_code(self.db, room_id)
            if game_session is not None:
                raise InvalidOperationError(
                    "Гостевой вход в игровую сессию отключён. Требуется авторизация."
                )
            resolved_name = self.guest_username(username)
            user_id = self.room_manager.join_room(room_id, resolved_name, is_guest=True)
            if user_id is None:
                raise SessionNotFoundError("Комната не найдена или игра уже началась")
            return {"user_id": user_id, "username": resolved_name}

        try:
            self.game_session_service.join_by_invite_code(room_id, current_user.id)
        except AlreadyParticipantError:
            pass

        room = self.ensure_runtime_room(room_id)

        if room is None:
            raise SessionNotFoundError("Комната не найдена или игра уже началась")

        user_id = self.room_manager.join_room(
            room_id=room_id,
            username=current_user.username or current_user.email,
            is_guest=False,
            email=current_user.email,
            user_id=str(current_user.id),
        )

        if user_id is None:
            raise InvalidOperationError("Комната не найдена или игра уже началась")

        return {"user_id": user_id}

    async def start_room(
        self,
        room_id: str,
        user_id: str | None,
        current_user: models.User | None,
    ) -> dict[str, str]:
        room = self.ensure_runtime_room(room_id)
        if room is None:
            raise SessionNotFoundError("Комната не найдена")

        host = room.participants.get(room.host_user_id)
        if host is None:
            raise InvalidOperationError("Хост комнаты не найден")

        if host.is_guest:
            if user_id != room.host_user_id:
                raise AccessDeniedError("Только хост может запустить игру")
        else:
            if current_user is None or current_user.email != host.email:
                raise AccessDeniedError("Только хост может запустить игру (требуется авторизация)")
            self.game_session_service.start_session_by_invite_code(room_id, current_user.id)

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
        if participant.is_guest or participant.email is None:
            return True

        game_session = get_game_session_by_invite_code(self.db, room_id)
        if game_session is None:
            return False

        user = get_user_by_email(self.db, participant.email)
        if user is None:
            return False

        if str(user.id) != user_id:
            return False

        return is_participant(self.db, game_session.id, user.id)

    def _rebuild_runtime_room(self, invite_code: str) -> Room | None:
        game_session = get_game_session_by_invite_code(self.db, invite_code)
        if game_session is None:
            return None

        host = game_session.host_user
        host_username = host.username or host.email

        room_status_user = str(game_session.host_user_id)
        try:
            self.room_manager.create_room(
                host_username=host_username,
                is_guest=False,
                email=host.email,
                room_id=invite_code,
                user_id=room_status_user,
            )
        except ValueError:
            existing_room = self.room_manager.get_room(invite_code)
            if existing_room is not None:
                return existing_room
            raise

        room = self.room_manager.get_room(invite_code)
        if room is None:
            return None

        participants = self.game_session_service.list_participants(game_session.id)
        for participant in participants:
            participant_id = str(participant.user_id)
            if participant_id in room.participants:
                continue
            username = participant.user.username or participant.user.email
            room.add_participant(
                participant_id,
                Participant.authenticated(username=username, email=participant.user.email),
            )

        if game_session.status == SessionStatus.PLAYING:
            self.room_manager.start_game(invite_code)
        elif game_session.status in (SessionStatus.FINISHED, SessionStatus.CANCELLED):
            self.room_manager.finish_game(invite_code)

        return room
