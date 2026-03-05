import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import models, settings
from backend.database import get_db

logger = logging.getLogger(__name__)

# Указывает на эндпоинт входа, чтобы Swagger UI знал, где получать токены
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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
        username: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        if username is None or token_type != "access":
            raise credentials_exception

        user = db.execute(
            select(models.User).where(models.User.email == username)
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
