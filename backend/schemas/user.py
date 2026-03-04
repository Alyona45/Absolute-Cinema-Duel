from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    """Schema for incoming registration request body."""

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
    """Schema for the response returned after successful registration.
    Never includes sensitive fields like password_hash.
    """

    id: int
    email: str
    username: str
    created_at: datetime

    class Config:
        # Allows Pydantic to read data from SQLAlchemy model attributes
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user data by ID (admin). All fields optional."""

    username: str | None = None
    password: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str | None) -> str | None:
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserProfileUpdate(BaseModel):
    """Schema for PATCH /users/me — profile update.
    Password is intentionally excluded; use /change-password instead.
    """

    username: str | None = None
    email: EmailStr | None = None


class ChangePasswordRequest(BaseModel):
    """Schema for POST /change-password."""

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        return v


class Token(BaseModel):
    """Schema for the JWT token response returned after login."""

    access_token: str
    token_type: str
