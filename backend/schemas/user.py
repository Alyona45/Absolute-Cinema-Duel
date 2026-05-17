from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema для тела запроса при регистрации."""

    email: EmailStr
    password: str = Field(min_length=8)
    username: str = Field(min_length=2, max_length=64)


class UserResponse(BaseModel):
    """Schema ответа после успешной регистрации или получения профиля.
    Никогда не включает чувствительные поля вроде password_hash.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str = Field(max_length=64)
    avatar_url: str | None = None
    is_admin: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Schema для обновления данных пользователя по ID (эндпоинт администратора). Все поля опциональны."""

    username: str | None = Field(default=None, min_length=2, max_length=64)
    password: str | None = Field(default=None, min_length=8)


class UserProfileUpdate(BaseModel):
    """Schema для PATCH /users/me — обновление профиля.
    Пароль намеренно исключён; используйте /change-password.
    """

    username: str | None = Field(default=None, min_length=2, max_length=64)
    email: EmailStr | None = None
    avatar_url: str | None = None


class ChangePasswordRequest(BaseModel):
    """Schema для POST /change-password."""

    current_password: str
    new_password: str = Field(min_length=8)


class Token(BaseModel):
    """Schema ответа с токенами, возвращаемая после входа."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]
