"""
Модели данных для WebSocket-комнат (in-memory).
Структура комнаты и участников для real-time взаимодействия.
"""

import enum
import time
from dataclasses import dataclass, field


class RoomStatus(str, enum.Enum):
    """Statuses of an in-memory room."""
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"


@dataclass
class Participant:
    """Участник комнаты: имя, статус подключения, гость или нет."""
    username: str
    connected: bool = True
    is_guest: bool = False
    email: str | None = None  # Для зарегистрированных пользователей — для верификации JWT

    def __post_init__(self) -> None:
        if self.is_guest and self.email is not None:
            raise ValueError("Guest participant must not have email")
        if not self.is_guest and self.email is None:
            raise ValueError("Authenticated participant must have email")

    @classmethod
    def guest(cls, username: str) -> "Participant":
        return cls(username=username, is_guest=True, email=None)

    @classmethod
    def authenticated(cls, username: str, email: str) -> "Participant":
        return cls(username=username, is_guest=False, email=email)


@dataclass
class Room:
    """
    Игровая комната (in-memory).
    Хранит участников и статус для real-time взаимодействия через WebSocket.
    """
    host_user_id: str
    participants: dict[str, Participant] = field(default_factory=dict)
    status: RoomStatus = RoomStatus.WAITING
    last_activity: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.host_user_id not in self.participants:
            raise ValueError("host_user_id must be present in participants")

    def touch(self) -> None:
        self.last_activity = time.time()

    def change_status(self, new_status: RoomStatus) -> None:
        allowed_transitions = {
            RoomStatus.WAITING: {RoomStatus.PLAYING, RoomStatus.FINISHED},
            RoomStatus.PLAYING: {RoomStatus.FINISHED},
            RoomStatus.FINISHED: set(),
        }

        if new_status not in allowed_transitions[self.status]:
            raise ValueError(f"Invalid status transition {self.status} -> {new_status}")

        self.status = new_status
        self.touch()

    def add_participant(self, user_id: str, participant: Participant) -> None:
        self.participants[user_id] = participant
        self.touch()

    def remove_participant(self, user_id: str) -> None:
        if user_id == self.host_user_id:
            raise ValueError("Cannot remove room host")
        self.participants.pop(user_id, None)
        self.touch()

    def set_connected(self, user_id: str, connected: bool) -> None:
        participant = self.participants.get(user_id)
        if participant is None:
            return
        participant.connected = connected
        self.touch()

    def to_dict(self) -> dict:
        """Сериализация комнаты в словарь для отправки клиентам."""
        return {
            "host_user_id": self.host_user_id,
            "participants": {
                uid: {
                    "username": p.username,
                    "connected": p.connected,
                    "is_guest": p.is_guest,
                }
                for uid, p in self.participants.items()
            },
            "status": self.status.value,
        }
