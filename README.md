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
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`

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