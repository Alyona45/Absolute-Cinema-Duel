import logging

from jose import JWTError, jwt

from backend import settings
from backend.websocket.models import Participant

logger = logging.getLogger(__name__)


def authenticate_ws_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if email is None or token_type != "access":
            logger.warning(
                "WS-аутентификация: невалидный токен (sub=%s, type=%s)",
                email,
                token_type,
            )
            return None
        return email
    except jwt.ExpiredSignatureError:
        logger.warning("WS-аутентификация: токен истёк")
        return None
    except JWTError as exc:
        logger.warning("WS-аутентификация: ошибка JWT — %s", exc)
        return None


def validate_ws_participant_token(participant: Participant, token: str | None) -> str | None:
    if participant.is_guest:
        return None

    if not token:
        return "Невалидный или отсутствующий токен"

    token_email = authenticate_ws_token(token)
    if token_email is None:
        return "Невалидный или отсутствующий токен"

    if token_email != participant.email:
        return "Токен не соответствует участнику комнаты"

    return None
