from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, TIMESTAMP, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()
    
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(320), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    username = Column(String(64))
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())
    
    auth_sessions = relationship("AuthSession", back_populates="user")
    
    # Индекс на поле email (оно уникально, но можно добавить индекс для скорости)
    __table_args__ = (Index('idx_users_email', 'email'),)

class AuthSession(Base):
    __tablename__ = 'auth_sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    refresh_token_hash = Column(String(255), nullable=False)
    expires_at = Column(TIMESTAMP, nullable=False)

    user = relationship("User", back_populates="auth_sessions")

    # Все индексы в одном __table_args__
    __table_args__ = (
        Index('idx_auth_sessions_user_id', 'user_id'),
        Index('refresh_token_hash_unique', 'refresh_token_hash', unique=True)
    )
    
class Movie(Base):
    __tablename__ = 'movies'

    id = Column(Integer, primary_key=True)
    kinopoisk_id = Column(Integer, nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    poster_url = Column(String(1024))
    year = Column(Integer)
    runtime = Column(Integer)
    rating = Column(Float)
    cached_at = Column(TIMESTAMP, nullable=False, default=func.now())

    # Уникальный индекс на kinopoisk_id
    __table_args__ = (Index('idx_movies_kinopoisk_id', 'kinopoisk_id', unique=True),)

class Genre(Base):
    __tablename__ = 'genres'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)

    # Индекс на поле name (оно уникально, но можно добавить индекс для скорости)
    __table_args__ = (Index('idx_genres_name', 'name'),)

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
    status = Column(String(16))  # CREATED, FINISHED, CANCELLED
    winner_session_movie_id = Column(Integer, ForeignKey('session_movies.id'))
    started_at = Column(TIMESTAMP, nullable=False, default=func.now())
    finished_at = Column(TIMESTAMP)

    host_user = relationship("User")
    winner_session_movie = relationship("SessionMovie")

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
    session = relationship("GameSession")

    # Уникальный индекс для предотвращения повторов фильмов в одной сессии
    __table_args__ = (
        Index('session_movies_unique', 'session_id', 'movie_id', unique=True),
    )