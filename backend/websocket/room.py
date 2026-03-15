"""
Менеджер комнат (in-memory).
Управляет жизненным циклом: создание, подключение, смена статуса, очистка.
"""

import logging
import time
import uuid

from backend.websocket.models import Participant, Room, RoomStatus

logger = logging.getLogger(__name__)


class RoomManager:
    def __init__(self):
        self.rooms: dict[str, Room] = {}

    # ─────────────────── Создание / подключение ───────────────────

    def create_room(
        self,
        host_username: str,
        is_guest: bool = False,
        email: str | None = None,
    ) -> tuple[str, str]:
        """
        Создаёт новую комнату.
        Возвращает (room_id, user_id) — хост автоматически добавляется
        как первый участник. is_guest — гостевой ли это пользователь.
        email — email зарегистрированного пользователя (для верификации JWT).
        """
        room_id = uuid.uuid4().hex[:8]
        user_id = str(uuid.uuid4())

        host_participant = (
            Participant.guest(host_username)
            if is_guest
            else Participant.authenticated(host_username, email=self._require_email(email))
        )
        room = Room(host_user_id=user_id, participants={user_id: host_participant})
        room.touch()
        self.rooms[room_id] = room
        return room_id, user_id

    def join_room(
        self,
        room_id: str,
        username: str,
        is_guest: bool = False,
        email: str | None = None,
    ) -> str | None:
        """
        Добавляет участника в комнату.
        Возвращает user_id нового участника, или None если комната
        не найдена / игра уже началась. is_guest — гостевой ли это пользователь.
        email — email зарегистрированного пользователя (для верификации JWT).
        """
        room = self.rooms.get(room_id)
        if room is None or room.status != RoomStatus.WAITING:
            return None

        participant = (
            Participant.guest(username)
            if is_guest
            else Participant.authenticated(username, email=self._require_email(email))
        )

        user_id = str(uuid.uuid4())
        room.add_participant(user_id, participant)
        return user_id

    # ─────────────────── Получение данных ─────────────────────────

    def get_room(self, room_id: str) -> Room | None:
        """Возвращает комнату по ID или None."""
        return self.rooms.get(room_id)

    def participant_ids(self, room_id: str) -> list[str]:
        """Возвращает список user_id всех участников комнаты."""
        room = self.rooms.get(room_id)
        return list(room.participants.keys()) if room else []

    def connected_participant_ids(self, room_id: str) -> list[str]:
        """Возвращает список user_id только подключённых участников комнаты."""
        room = self.rooms.get(room_id)
        if room is None:
            return []
        return [
            user_id
            for user_id, participant in room.participants.items()
            if participant.connected
        ]

    # ─────────────────── Управление статусом ──────────────────────

    def start_game(self, room_id: str) -> bool:
        """
        Переводит комнату в статус PLAYING.
        Возвращает True при успехе, False если комната не найдена
        или не в статусе WAITING.
        """
        room = self.rooms.get(room_id)
        if room is None or room.status != RoomStatus.WAITING:
            return False

        room.change_status(RoomStatus.PLAYING)
        return True

    def finish_game(self, room_id: str) -> bool:
        """
        Переводит комнату в статус FINISHED.
        Возвращает True при успехе.
        """
        room = self.rooms.get(room_id)
        if room is None or room.status != RoomStatus.PLAYING:
            return False

        room.change_status(RoomStatus.FINISHED)
        return True

    # ─────────────────── Статус подключения ───────────────────────

    def set_connected(self, room_id: str, user_id: str, connected: bool):
        """Обновляет флаг connected для участника и last_activity."""
        room = self.rooms.get(room_id)
        if room:
            room.set_connected(user_id, connected)

    # ─────────────────── Очистка ──────────────────────────────────

    def cleanup_dead_rooms(self, max_inactive_seconds: int = 60) -> list[str]:
        """
        Удаляет комнаты, в которых все отключены и нет активности
        дольше max_inactive_seconds.
        Возвращает список удалённых room_id.
        """
        now = time.time()
        dead = []
        # Снимаем snapshot ключей, чтобы избежать RuntimeError при итерации
        for rid in list(self.rooms.keys()):
            room = self.rooms.get(rid)
            if room is None:
                continue
            all_disconnected = all(
                not p.connected for p in room.participants.values()
            )
            if all_disconnected and (now - room.last_activity > max_inactive_seconds):
                dead.append(rid)

        for rid in dead:
            self.rooms.pop(rid, None)
            logger.info("Комната %s удалена по TTL", rid)

        return dead

    @staticmethod
    def _require_email(email: str | None) -> str:
        if email is None:
            raise ValueError("Authenticated participant requires email")
        return email
