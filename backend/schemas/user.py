from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema для тела запроса при регистрации."""

    email: EmailStr
    password: str = Field(min_length=8)
    username: str


class UserResponse(BaseModel):
    """Schema ответа после успешной регистрации или получения профиля.
    Никогда не включает чувствительные поля вроде password_hash.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    created_at: datetime


class UserUpdate(BaseModel):
    """Schema для обновления данных пользователя по ID (эндпоинт администратора). Все поля опциональны."""

    username: str | None = None
    password: str | None = Field(default=None, min_length=8)


class UserProfileUpdate(BaseModel):
    """Schema для PATCH /users/me — обновление профиля.
    Пароль намеренно исключён; используйте /change-password.
    """

    username: str | None = None
    email: EmailStr | None = None


class ChangePasswordRequest(BaseModel):
    """Schema для POST /change-password."""

    current_password: str
    new_password: str = Field(min_length=8)


class Token(BaseModel):
    """Schema ответа с токенами, возвращаемая после входа."""

    access_token: str
    refresh_token: str
    token_type: str
