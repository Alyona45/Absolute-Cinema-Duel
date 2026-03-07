from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.models import User
from backend.schemas.user import UserCreate, UserUpdate, UserProfileUpdate

# bcrypt — отраслевой стандарт хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Хеширует пароль в открытом виде с помощью bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Возвращает True, если пароль в открытом виде совпадает с сохранённым хешем."""
    return pwd_context.verify(plain, hashed)


def get_user_by_email(db: Session, email: str) -> User | None:
    """Возвращает пользователя по email или None, если не найден."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    """Возвращает пользователя по имени пользователя или None, если не найден."""
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Возвращает пользователя, если учётные данные верны, иначе None."""
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Создаёт нового пользователя в базе данных.
    Хеширует пароль перед сохранением — пароль в открытом виде никогда не записывается.
    """
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hash_password(user_data.password),
    )
    db.add(db_user)
    db.commit()
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
        user.username = update_data.username

    if update_data.password is not None:
        user.password_hash = hash_password(update_data.password)

    db.commit()
    db.refresh(user)
    return user


def update_user_profile(db: Session, user: User, update_data: UserProfileUpdate) -> User:
    """
    Обновляет поля профиля текущего аутентифицированного пользователя.
    Пароль не принимается — используйте change_password().
    Уникальность username и email проверяется на уровне роутера перед вызовом этой функции.
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
    Проверяет текущий пароль, затем заменяет его новым.
    Возвращает False, если current_password неверен.
    """
    if not verify_password(current_password, user.password_hash):
        return False

    user.password_hash = hash_password(new_password)
    db.commit()
    return True


def delete_user(db: Session, user: User) -> None:
    """Безвозвратно удаляет пользователя из базы данных."""
    db.delete(user)
    db.commit()
