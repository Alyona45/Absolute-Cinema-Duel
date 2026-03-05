A gaming web platform that allows companies to select a film through a gamified elimination process. 

## Setup для коллег

### 1. Клонировать проект
```bash
git clone https://github.com/Alyona45/Absolute-Cinema-Duel
cd absolute-cinema-duel
```

### 2. Версия Python
```text
3.12.3
```

### 3. Создать и активировать venv
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Установить зависимости
```bash
pip install -U pip
pip install -e .
```

### 5. Настроить переменные окружения
```bash
cp .env_template .env
```

Заполнить в `.env`:
- `DATABASE_URL` — строка подключения к PostgreSQL, например:
  `postgresql://user:password@localhost:5432/absolute_cinema_duel`
- `SECRET_KEY` — секретный ключ для подписи JWT
- `ALGORITHM` — алгоритм JWT (по умолчанию `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` — время жизни access-токена в минутах (по умолчанию `30`)
- `REFRESH_TOKEN_EXPIRE_DAYS` — время жизни refresh-токена в днях (по умолчанию `30`)

### 6. Подготовить PostgreSQL
Создать БД (пример):
```bash
createdb -h localhost -p 5432 -U postgres absolute_cinema_duel
```

### 7. Применить миграции
```bash
alembic -c alembic.ini upgrade head
```

Проверка (без изменений в БД):
```bash
alembic -c alembic.ini history
alembic -c alembic.ini upgrade head --sql
```

## Важно
- Коммитить миграции из `backend/alembic/versions/`.
- У каждого разработчика своя локальная БД, схема синхронизируется миграциями.