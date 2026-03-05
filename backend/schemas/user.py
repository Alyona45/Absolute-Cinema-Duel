from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    """Schema для тела запроса при регистрации."""

    email: EmailStr
    password: str
    username: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserResponse(BaseModel):
    """Schema ответа после успешной регистрации или получения профиля.
    Никогда не включает чувствительные поля вроде password_hash.
    """

    id: int
    email: str
    username: str
    created_at: datetime

    class Config:
        # Позволяет Pydantic читать данные из атрибутов SQLAlchemy-модели
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema для обновления данных пользователя по ID (эндпоинт администратора). Все поля опциональны."""

    username: str | None = None
    password: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str | None) -> str | None:
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserProfileUpdate(BaseModel):
    """Schema для PATCH /users/me — обновление профиля.
    Пароль намеренно исключён; используйте /change-password.
    """

    username: str | None = None
    email: EmailStr | None = None


class ChangePasswordRequest(BaseModel):
    """Schema для POST /change-password."""

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        return v


class Token(BaseModel):
    """Schema ответа с токенами, возвращаемая после входа."""

    access_token: str
    refresh_token: str
    token_type: str
