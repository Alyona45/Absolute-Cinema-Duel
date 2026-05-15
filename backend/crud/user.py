import logging

from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import User
from backend.schemas.user import UserCreate, UserUpdate, UserProfileUpdate

# bcrypt — отраслевой стандарт хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)


def _commit(db: Session, action: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Ошибка БД при %s", action)
        raise


def hash_password(password: str) -> str:
    """Хеширует пароль в открытом виде с помощью bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Возвращает True, если пароль в открытом виде совпадает с сохранённым хешем."""
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        logger.exception("Ошибка проверки хеша пароля")
        return False


def get_user_by_email(db: Session, email: str) -> User | None:
    """Возвращает пользователя по email или None, если не найден."""
    normalized_email = email.strip().lower()
    return db.query(User).filter(func.lower(User.email) == normalized_email).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    """Возвращает пользователя по имени пользователя или None, если не найден."""
    normalized_username = username.strip().lower()
    return db.query(User).filter(func.lower(User.username) == normalized_username).first()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Возвращает пользователя, если учётные данные верны, иначе None."""
    normalized_email = email.strip().lower()
    user = get_user_by_email(db, normalized_email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Создаёт нового пользователя в базе данных.
    Хеширует пароль перед сохранением — пароль в открытом виде никогда не записывается.
    """
    db_user = User(
        email=user_data.email.strip().lower(),
        username=user_data.username.strip(),
        password_hash=hash_password(user_data.password),
    )
    db.add(db_user)
    _commit(db, "создании пользователя")
    db.refresh(db_user)  # Перезагружаем объект, чтобы получить поля, сгенерированные БД (например, id, created_at)
    return db_user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Возвращает пользователя по первичному ключу или None, если не найден."""
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user: User, update_data: UserUpdate) -> User:
    """
    Обновляет разрешённые поля пользователя (эндпоинт администратора).
    Изменяются только явно переданные поля (не None).
    """
    if update_data.username is not None:
        user.username = update_data.username.strip()

    if update_data.password is not None:
        user.password_hash = hash_password(update_data.password)

    _commit(db, "обновлении пользователя")
    db.refresh(user)
    return user


def update_user_profile(db: Session, user: User, update_data: UserProfileUpdate) -> User:
    """
    Обновляет поля профиля текущего аутентифицированного пользователя.
    Пароль не принимается — используйте change_password().
    Уникальность username и email проверяется на уровне роутера перед вызовом этой функции.
    """
    if update_data.username is not None:
        user.username = update_data.username.strip()

    if update_data.email is not None:
        user.email = update_data.email.strip().lower()

    if update_data.avatar_url is not None:
        user.avatar_url = update_data.avatar_url

    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> bool:
    """
    Проверяет текущий пароль, затем заменяет его новым.
    Возвращает False, если current_password неверен.
    """
    if not verify_password(current_password, user.password_hash):
        return False

    user.password_hash = hash_password(new_password)
    _commit(db, "смене пароля пользователя")
    return True


def delete_user(db: Session, user: User) -> None:
    """Безвозвратно удаляет пользователя из базы данных."""
    db.delete(user)
    _commit(db, "удалении пользователя")


def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    """Возвращает список всех пользователей с пагинацией (для админки)."""
    return db.query(User).offset(skip).limit(limit).all()


def set_admin(db: Session, user: User, is_admin: bool) -> User:
    """Устанавливает или снимает флаг администратора для пользователя."""
    user.is_admin = is_admin
    _commit(db, "изменении флага администратора")
    db.refresh(user)
    return user
