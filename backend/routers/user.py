from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend import models
from backend.database import get_db
from backend.schemas.user import ChangePasswordRequest, UserProfileUpdate, UserResponse, UserUpdate
from backend.crud.user import (
    change_password,
    get_user_by_id,
    update_user,
    update_user_profile,
    delete_user,
)
from backend.security import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


def get_user_or_404(user_id: int, db: Session = Depends(get_db)):
    """Shared dependency — returns the user or raises 404."""
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
    """Return the profile of the currently authenticated user."""
    return current_user


@router.patch("/me", response_model=UserResponse)
def edit_me(
    update_data: UserProfileUpdate,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Update the current user's profile (username, email).
    Password changes are rejected — use POST /users/change-password.
    """
    return update_user_profile(db, current_user, update_data)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(
    request: ChangePasswordRequest,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> None:
    """Change password for the currently authenticated user."""
    ok = change_password(db, current_user, request.current_password, request.new_password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )


@router.get("/{user_id}", response_model=UserResponse)
def read_user(user=Depends(get_user_or_404)) -> UserResponse:
    """Get a user by ID."""
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def edit_user(
    update_data: UserUpdate,
    user=Depends(get_user_or_404),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Update username and/or password by ID. Only provided fields will be changed."""
    return update_user(db, user, update_data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(user=Depends(get_user_or_404), db: Session = Depends(get_db)) -> None:
    """Permanently delete a user."""
    delete_user(db, user)
