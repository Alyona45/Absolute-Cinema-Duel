import enum
from sqlalchemy import Boolean, Column, Enum as SQLEnum, Float, ForeignKey, Index, Integer, String, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class SessionStatus(str, enum.Enum):
    CREATED = "CREATED"
    PLAYING = "PLAYING"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"
    
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(320), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    username = Column(String(64))
    avatar_url = Column(Text, nullable=True)
    # Флаг администратора — только True/False, по умолчанию обычный пользователь
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())

    auth_sessions = relationship("AuthSession", back_populates="user")

class AuthSession(Base):
    """Хранит активные сессии с refresh-токенами.  
    Позволяет инвалидировать сессии при выходе или компрометации токена.
    """
    __tablename__ = 'auth_sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    # Хранится только хэш токена — сырое значение не сохраняется
    refresh_token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)

    user = relationship("User", back_populates="auth_sessions")

    # Индекс для быстрого поиска по user_id
    __table_args__ = (
        Index('idx_auth_sessions_user_id', 'user_id'),
    )
    
class Movie(Base):
    __tablename__ = 'movies'

    id = Column(Integer, primary_key=True)
    kinopoisk_id = Column(Integer, nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    short_description = Column(Text)
    description = Column(Text)
    poster_url = Column(String(1024))
    year = Column(Integer)
    runtime = Column(Integer)
    rating = Column(Float)
    cached_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    genre_links = relationship("MovieGenre")

class Genre(Base):
    __tablename__ = 'genres'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)

class MovieGenre(Base):
    __tablename__ = 'movie_genres'

    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, ForeignKey('movies.id'), nullable=False)
    genre_id = Column(Integer, ForeignKey('genres.id'), nullable=False)

    movie = relationship("Movie")
    genre = relationship("Genre")

    # Уникальный составной индекс для предотвращения повторов в movie_id и genre_id
    __table_args__ = (
        Index('movie_genres_unique', 'movie_id', 'genre_id', unique=True),
    )

class GameSession(Base):
    __tablename__ = 'game_sessions'

    id = Column(Integer, primary_key=True)
    host_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    invite_code = Column(String(12), nullable=False, unique=True)
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.CREATED)
    winner_session_movie_id = Column(Integer, ForeignKey('session_movies.id'))
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    finished_at = Column(TIMESTAMP(timezone=True))

    host_user = relationship("User")
    # foreign_keys is required because there are two FK paths between game_sessions and session_movies
    winner_session_movie = relationship("SessionMovie", foreign_keys=[winner_session_movie_id])

    # Индекс для быстрого поиска по host_user_id
    __table_args__ = (Index('idx_game_sessions_host_user_id', 'host_user_id'),)

class SessionParticipant(Base):
    __tablename__ = 'session_participants'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_id = Column(Integer, ForeignKey('game_sessions.id'), nullable=False)

    user = relationship("User")
    session = relationship("GameSession")

    # Уникальный индекс для предотвращения дублирования участников
    __table_args__ = (
        Index('session_participants_unique', 'session_id', 'user_id', unique=True),
    )

class SessionMovie(Base):
    __tablename__ = 'session_movies'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('game_sessions.id'), nullable=False)
    movie_id = Column(Integer, ForeignKey('movies.id'), nullable=False)
    proposed_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    movie = relationship("Movie")
    proposed_by_user = relationship("User")
    # foreign_keys is required because there are two FK paths between session_movies and game_sessions
    session = relationship("GameSession", foreign_keys=[session_id])
