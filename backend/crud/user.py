from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.models import User
from backend.schemas.user import UserCreate, UserUpdate, UserProfileUpdate

# bcrypt is the hashing algorithm — industry standard for passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain-text password matches the stored hash."""
    return pwd_context.verify(plain, hashed)


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return a user by email, or None if not found."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    """Return a user by username, or None if not found."""
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return the user if credentials are valid, otherwise None."""
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Create a new user in the database.
    Hashes the password before storing — plain-text is never saved.
    """
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hash_password(user_data.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)  # Reload the object to get DB-generated fields (e.g. id, created_at)
    return db_user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Return a user by primary key, or None if not found."""
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user: User, update_data: UserUpdate) -> User:
    """
    Update allowed user fields (admin endpoint).
    Only fields explicitly provided (not None) will be changed.
    """
    if update_data.username is not None:
        user.username = update_data.username

    if update_data.password is not None:
        user.password_hash = hash_password(update_data.password)

    db.commit()
    db.refresh(user)
    return user


def update_user_profile(db: Session, user: User, update_data: UserProfileUpdate) -> User:
    """
    Update profile fields for the currently authenticated user.
    Password is not accepted here — use change_password() instead.
    """
    if update_data.username is not None:
        user.username = update_data.username

    if update_data.email is not None:
        user.email = update_data.email

    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> bool:
    """
    Verify the current password, then replace it with the new one.
    Returns False if current_password is wrong.
    """
    if not verify_password(current_password, user.password_hash):
        return False

    user.password_hash = hash_password(new_password)
    db.commit()
    return True


def delete_user(db: Session, user: User) -> None:
    """Permanently delete a user from the database."""
    db.delete(user)
    db.commit()
