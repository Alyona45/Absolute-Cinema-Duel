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
        room = Room(host_user_id=user_id)
        room.participants[user_id] = Participant(
            username=host_username, is_guest=is_guest, email=email,
        )
        room.last_activity = time.time()
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
        room.last_activity = time.time()
        user_id = str(uuid.uuid4())
        room.participants[user_id] = Participant(
            username=username, is_guest=is_guest, email=email,
        )
        return user_id

    # ─────────────────── Получение данных ─────────────────────────

    def get_room(self, room_id: str) -> Room | None:
        """Возвращает комнату по ID или None."""
        return self.rooms.get(room_id)

    def participant_ids(self, room_id: str) -> list[str]:
        """Возвращает список user_id всех участников комнаты."""
        room = self.rooms.get(room_id)
        return list(room.participants.keys()) if room else []

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
        room.status = RoomStatus.PLAYING
        room.last_activity = time.time()
        return True

    def finish_game(self, room_id: str) -> bool:
        """
        Переводит комнату в статус FINISHED.
        Возвращает True при успехе.
        """
        room = self.rooms.get(room_id)
        if room is None or room.status != RoomStatus.PLAYING:
            return False
        room.status = RoomStatus.FINISHED
        room.last_activity = time.time()
        return True

    # ─────────────────── Статус подключения ───────────────────────

    def set_connected(self, room_id: str, user_id: str, connected: bool):
        """Обновляет флаг connected для участника и last_activity."""
        room = self.rooms.get(room_id)
        if room and user_id in room.participants:
            room.participants[user_id].connected = connected
            room.last_activity = time.time()

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
