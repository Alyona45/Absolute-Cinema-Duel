# Absolute Cinema Duel

Backend-сервис для выбора фильма в компании: пользователи создают игровую сессию, добавляют фильмы и выбирают победителя.  
Проект построен на FastAPI + PostgreSQL, с JWT-аутентификацией и real-time комнатами через WebSocket.

## Что реализовано

- Регистрация, логин, refresh/logout с ротацией refresh-токенов.
- Профиль пользователя, смена пароля, загрузка аватара.
- Роли: обычный пользователь и администратор.
- Хранение фильмов и жанров, кеширование метаданных фильма.
- Игровые сессии: участники, список фильмов, выбор победителя.
- In-memory комнаты для real-time сценариев (WebSocket).

## Технологии

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Pydantic v2
- python-jose (JWT)
- Passlib (bcrypt)
- httpx

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/Alyona45/Absolute-Cinema-Duel
cd Absolute-Cinema-Duel
```

### 2. Создать виртуальное окружение

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Установить зависимости

```bash
python -m pip install -U pip
pip install -e .
```

Для корректной работы WebSocket нужен `uvicorn[standard]`.
Он уже включён в зависимости проекта; после pull обновлений
переустановите пакет в текущем окружении командой `pip install -e .`.

### 4. Настроить переменные окружения

```bash
cp .env_template .env
```

Если вы на Windows и нет `cp`, используйте:

```powershell
Copy-Item .env_template .env
```

Заполните `.env` (см. таблицу ниже).

### 5. Подготовить PostgreSQL

Создайте базу данных и укажите корректный `DATABASE_URL`.

Пример URL:

```text
postgresql+psycopg2://your_db_user:your_db_password@localhost:5432/your_db_name
```

### 6. Применить миграции

```bash
alembic -c alembic.ini upgrade head
```

### 7. Запустить API

```bash
uvicorn backend.main:app --reload
```

После запуска:

- Demo UI: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### 8. Открыть демо-фронт

После старта API откройте в браузере:

```text
http://127.0.0.1:8000/
```

В UI доступны формы для:

- auth (register/login/refresh/logout);
- профиля и загрузки аватара;
- фильмов и жанров;
- игровых сессий (участники, предложения фильмов, выбор победителя);
- комнат и WebSocket (create/join/start, connect/ping/log).

## Переменные окружения

| Переменная | Обязательна | Описание |
|---|---|---|
| `DATABASE_URL` | Да | Строка подключения к PostgreSQL |
| `SECRET_KEY` | Да | Секрет для подписи JWT |
| `ALGORITHM` | Нет | Алгоритм JWT, по умолчанию `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Нет | TTL access-токена в минутах (по умолчанию `30`) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Нет | TTL refresh-токена в днях (по умолчанию `30`) |
| `KINOPOISK_API_KEY` | Нет | API-ключ kinopoisk.dev (для интеграции с внешним API) |

Генерация `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Карта API

Ниже перечислены основные эндпоинты. Полные схемы запросов/ответов смотрите в `/docs`.

### Auth (`/auth`)

- `POST /auth/register` - регистрация пользователя.
- `POST /auth/login` - логин (OAuth2 password form, поле `username` = email).
- `POST /auth/refresh` - получить новую пару токенов по refresh-токену.
- `POST /auth/logout` - инвалидировать refresh-сессию.

### Users (`/users`)

- `GET /users/me` - профиль текущего пользователя.
- `PATCH /users/me` - обновление профиля (username/email/avatar_url).
- `POST /users/me/avatar` - загрузить аватар (до 5 MB; `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`).
- `POST /users/change-password` - смена пароля.
- `GET /users/{user_id}` - получить пользователя (только админ).
- `PATCH /users/{user_id}` - изменить пользователя (только админ).
- `DELETE /users/{user_id}` - удалить пользователя (только админ).

### Movies (`/movies`)

- `POST /movies/` - создать/получить фильм по `kinopoisk_id` (требуется авторизация).
- `GET /movies/kinopoisk/{kinopoisk_id}` - получить фильм по ID Кинопоиска.
- `GET /movies/{movie_id}` - получить фильм по внутреннему ID.
- `PATCH /movies/{movie_id}` - обновить кеш фильма (требуется авторизация).
- `GET /movies/genres/all` - список всех жанров.
- `GET /movies/{movie_id}/genres` - жанры фильма.
- `PUT /movies/{movie_id}/genres` - синхронизировать жанры фильма (требуется авторизация).

### Game Sessions (`/sessions`)

- `POST /sessions/` - создать игровую сессию (хост = текущий пользователь).
- `GET /sessions/my/list` - список сессий, где пользователь хост.
- `GET /sessions/{session_id}` - получить сессию.
- `POST /sessions/{session_id}/winner` - выбрать победителя (только хост).
- `POST /sessions/{session_id}/participants` - войти в сессию.
- `DELETE /sessions/{session_id}/participants` - выйти из сессии.
- `GET /sessions/{session_id}/participants` - список участников.
- `POST /sessions/{session_id}/movies` - предложить фильм (только участник).
- `DELETE /sessions/{session_id}/movies/{session_movie_id}` - убрать фильм (автор или хост).
- `GET /sessions/{session_id}/movies` - список фильмов в сессии.

### Rooms + WebSocket

HTTP:

- `POST /rooms` - создать комнату (авторизованный или гостевой пользователь).
- `POST /rooms/{room_id}/join` - присоединиться к комнате.
- `POST /rooms/{room_id}/start` - запустить игру (только хост).
- `GET /rooms/{room_id}` - получить состояние комнаты.

WebSocket:

```text
ws://<host>/ws/{room_id}/{user_id}?token=<JWT_ACCESS_TOKEN>
```

- Для зарегистрированных пользователей `token` обязателен.
- Для гостей подключение возможно без токена.

События клиент -> сервер:

- `{"type": "PING"}`

События сервер -> клиент:

- `ROOM_STATE`
- `PLAYER_JOINED`
- `PLAYER_DISCONNECTED`
- `GAME_STARTED`
- `PONG`
- `ERROR`

`POST /rooms/{room_id}/start` возвращает `200 OK` и в ответе содержит
статистику доставки события `GAME_STARTED` для подключённых участников.

## Миграции

Применить все:

```bash
alembic -c alembic.ini upgrade head
```

История миграций:

```bash
alembic -c alembic.ini history
```

Сгенерировать новую ревизию:

```bash
alembic -c alembic.ini revision -m "describe_change"
```

## Структура проекта

```text
backend/
  routers/        HTTP и WebSocket маршруты
  crud/           Операции с БД
  schemas/        Pydantic-схемы запросов/ответов
  services/       Прикладные сервисы (кинопоиск, аватары)
  websocket/      In-memory модели комнат и connection manager
  alembic/        Миграции БД
frontend/         Демо UI (HTML/CSS/JS)
storage/avatars/  Локальное хранилище аватаров
```

## Нюансы реализации

- Access/refresh токены различаются полем `type` в JWT (`access`/`refresh`).
- Refresh-токен хранится в БД только как SHA-256 хеш.
- При `refresh` используется ротация: старая сессия удаляется, новая создаётся.
- In-memory комнаты очищаются фоновым циклом каждые 60 секунд, если все участники оффлайн и не было активности.

## Текущее состояние

- Репозиторий содержит backend-часть и миграции.
- Автоматические тесты в проекте пока не добавлены.