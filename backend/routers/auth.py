import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Annotated

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend import settings
from backend.database import get_db
from backend.models import AuthSession
from backend.schemas.user import Token, UserCreate, UserResponse
from backend.crud.user import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_username,
    hash_password,
    verify_password,
)
from backend.security import create_access_token, create_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])


def get_refresh_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(user_data: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """
    Регистрирует нового пользователя.
    Возвращает 400, если email или имя пользователя уже заняты.
    """
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken",
        )

    return create_user(db, user_data)


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
) -> Token:
    """
    Аутентификация по email + паролю (OAuth2 password flow).
    Возвращает access- и refresh-токены при успехе.
    """
    # OAuth2PasswordRequestForm использует поле 'username' — трактуем его как email
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})

    # Сохраняем хеш refresh-токена в БД для возможности инвалидации
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    session = AuthSession(
        user_id=user.id,
        refresh_token_hash=get_refresh_token_hash(refresh_token),
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()

    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/refresh", response_model=Token)
def refresh_tokens(request: RefreshRequest, db: Session = Depends(get_db)) -> Token:
    """
    Выдаёт новую пару токенов по действующему refresh-токену.
    Старая сессия удаляется — реализован паттерн «ротации refresh-токенов».
    """
    refresh_token = request.refresh_token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительный или истёкший refresh-токен",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        if email is None or token_type != "refresh":
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh-токен истёк",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except JWTError:
        raise credentials_exception from None

    user = get_user_by_email(db, email)
    if user is None:
        raise credentials_exception

    token_hash = get_refresh_token_hash(refresh_token)
    matching_session = db.query(AuthSession).filter(
        AuthSession.user_id == user.id,
        AuthSession.refresh_token_hash == token_hash
    ).first()

    if matching_session is None:
        raise credentials_exception

    if matching_session.expires_at < datetime.now(timezone.utc):
        db.delete(matching_session)
        db.commit()
        raise credentials_exception

    # Удаляем старую сессию (ротация токенов)
    db.delete(matching_session)
    db.commit()

    # Создаём новую пару токенов и новую сессию
    new_access_token = create_access_token(data={"sub": user.email})
    new_refresh_token = create_refresh_token(data={"sub": user.email})

    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    new_session = AuthSession(
        user_id=user.id,
        refresh_token_hash=get_refresh_token_hash(new_refresh_token),
        expires_at=expires_at,
    )
    db.add(new_session)
    db.commit()

    return Token(access_token=new_access_token, refresh_token=new_refresh_token, token_type="bearer")


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(request: LogoutRequest, db: Session = Depends(get_db)):
    """
    Удаляет сессию пользователя (инвалидирует refresh-токен).
    """
    token_hash = get_refresh_token_hash(request.refresh_token)
    session = db.query(AuthSession).filter(AuthSession.refresh_token_hash == token_hash).first()
    
    if session:
        db.delete(session)
        db.commit()
    
    return {"detail": "Successfully logged out"}
