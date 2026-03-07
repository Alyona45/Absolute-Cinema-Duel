from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend import models
from backend.database import get_db
from backend.schemas.user import ChangePasswordRequest, UserProfileUpdate, UserResponse, UserUpdate
from backend.crud.user import (
    change_password,
    get_user_by_id,
    get_user_by_email,
    get_user_by_username,
    update_user,
    update_user_profile,
    delete_user,
)
from backend.security import get_admin_user, get_current_user

router = APIRouter(prefix="/users", tags=["users"])


def get_user_or_404(user_id: int, db: Session = Depends(get_db)):
    """Общая зависимость — возвращает пользователя или выбрасывает 404."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.get("/me", response_model=UserResponse)
def read_me(
    current_user: Annotated[models.User, Depends(get_current_user)],
) -> UserResponse:
    """Возвращает профиль текущего аутентифицированного пользователя."""
    return current_user


@router.patch("/me", response_model=UserResponse)
def edit_me(
    update_data: UserProfileUpdate,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Обновляет профиль текущего пользователя (имя, email).
    Смена пароля отклоняется — используйте POST /users/change-password.
    """
    # Проверяем уникальность username: нельзя занять имя другого пользователя
    if update_data.username is not None:
        existing = get_user_by_username(db, update_data.username)
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already taken",
            )

    # Проверяем уникальность email: нельзя занять адрес другого пользователя
    if update_data.email is not None:
        existing = get_user_by_email(db, update_data.email)
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )

    return update_user_profile(db, current_user, update_data)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(
    request: ChangePasswordRequest,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> None:
    """Меняет пароль текущего аутентифицированного пользователя."""
    ok = change_password(db, current_user, request.current_password, request.new_password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )


# --- Эндпоинты администратора (требуют флага is_admin) ---

@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    user=Depends(get_user_or_404),
    _: Annotated[models.User, Depends(get_admin_user)] = None,
) -> UserResponse:
    """Получить пользователя по ID. Только для администраторов."""
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def edit_user(
    update_data: UserUpdate,
    user=Depends(get_user_or_404),
    db: Session = Depends(get_db),
    _: Annotated[models.User, Depends(get_admin_user)] = None,
) -> UserResponse:
    """Обновить имя и/или пароль по ID. Только для администраторов."""
    return update_user(db, user, update_data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(
    user=Depends(get_user_or_404),
    db: Session = Depends(get_db),
    _: Annotated[models.User, Depends(get_admin_user)] = None,
) -> None:
    """Безвозвратно удалить пользователя. Только для администраторов."""
    delete_user(db, user)
