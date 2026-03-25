import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.actors import (
    GUEST_TOKEN_COOKIE,
    CurrentActor,
    generate_guest_id,
    generate_guest_name,
)
from backend import models, settings
from backend.database import get_db

logger = logging.getLogger(__name__)

# Указывает на эндпоинт входа, чтобы Swagger UI знал, где получать токены
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Опциональная схема — не выбрасывает 401 при отсутствии токена
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Кодирует JWT access-токен.
    'sub' — email пользователя; 'type' устанавливается в 'access'.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Кодирует JWT refresh-токен.
    'sub' — email пользователя; 'type' устанавливается в 'refresh'.
    Срок жизни значительно дольше, чем у access-токена.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_guest_token(
    guest_id: str,
    display_name: str,
    expires_delta: timedelta | None = None,
) -> str:
    to_encode = {
        "sub": guest_id,
        "name": display_name,
    }
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "guest"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_guest_token(token: str) -> CurrentActor | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        guest_id: str | None = payload.get("sub")
        display_name: str | None = payload.get("name")
        token_type: str | None = payload.get("type")

        if guest_id is None or display_name is None or token_type != "guest":
            return None

        return CurrentActor(
            user_id=None,
            guest_id=guest_id,
            display_name=display_name,
            email=None,
        )
    except JWTError:
        return None


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> models.User:
    """
    Зависимость: декодирует Bearer-токен и возвращает аутентифицированного пользователя.
    При любой ошибке валидации выбрасывает 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        if email is None or token_type != "access":
            raise credentials_exception

        user = db.execute(
            select(models.User).where(models.User.email == email)
        ).scalars().first()

        if user is None:
            raise credentials_exception

        return user

    except jwt.ExpiredSignatureError:
        logger.info("Срок действия access-токена истёк")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": 'Bearer error="token_expired"'},
        ) from None
    except JWTError as e:
        logger.error("Ошибка декодирования JWT: %s", e)
        raise credentials_exception from e


def get_admin_user(
    current_user: Annotated[models.User, Depends(get_current_user)],
) -> models.User:
    """
    Зависимость: проверяет, что текущий пользователь является администратором.
    Выбрасывает 403, если у пользователя нет прав администратора.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа",
        )
    return current_user


def get_current_user_optional(
    token: Annotated[str | None, Depends(oauth2_scheme_optional)],
    db: Annotated[Session, Depends(get_db)],
) -> models.User | None:
    """
    Опциональная аутентификация: возвращает пользователя если JWT
    присутствует и валиден, иначе None.
    Не выбрасывает исключений при отсутствии/невалидности токена.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        if email is None or token_type != "access":
            return None

        user = db.execute(
            select(models.User).where(models.User.email == email)
        ).scalars().first()
        return user
    except JWTError:
        return None


def get_current_actor_optional(
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)],
    guest_token: Annotated[str | None, Cookie(alias=GUEST_TOKEN_COOKIE)] = None,
) -> CurrentActor | None:
    if current_user is not None:
        return CurrentActor(
            user_id=current_user.id,
            guest_id=None,
            display_name=current_user.username or current_user.email,
            email=current_user.email,
        )

    if guest_token is not None:
        return decode_guest_token(guest_token)

    return None


def get_current_actor(
    current_actor: Annotated[CurrentActor | None, Depends(get_current_actor_optional)],
) -> CurrentActor:
    if current_actor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest or authenticated identity is required",
        )
    return current_actor


def ensure_guest_actor(
    response: Response,
    current_actor: CurrentActor | None,
    display_name: str | None = None,
) -> CurrentActor:
    if current_actor is not None and not current_actor.is_guest:
        return current_actor

    guest_id = current_actor.guest_id if current_actor is not None else generate_guest_id()
    resolved_name = display_name or (
        current_actor.display_name if current_actor is not None else generate_guest_name()
    )

    guest_actor = CurrentActor(
        user_id=None,
        guest_id=guest_id,
        display_name=resolved_name,
        email=None,
    )
    response.set_cookie(
        key=GUEST_TOKEN_COOKIE,
        value=create_guest_token(guest_id, resolved_name),
        httponly=True,
        samesite="lax",
    )
    return guest_actor
