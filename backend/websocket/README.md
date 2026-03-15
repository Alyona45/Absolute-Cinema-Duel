# WebSocket: протокол комнат

Документ описывает актуальный контракт для room-flow из `backend/routers/ws.py`.

## Подключение к WebSocket

```text
ws://<host>/ws/{room_id}/{user_id}?token=<JWT_ACCESS_TOKEN>
```

- `room_id` и `user_id` выдаются HTTP-методами создания/входа в комнату.
- `token` обязателен только для зарегистрированных пользователей.
- Для гостей `token` не нужен.

### Коды закрытия WebSocket

| Код | Причина |
|---|---|
| `4001` | Невалидный или отсутствующий токен у зарегистрированного участника |
| `4004` | Комната не найдена или `user_id` не принадлежит комнате |
| `1011` | Внутренняя ошибка сервера при установке соединения |

## HTTP API комнат

В текущей реализации нет отдельных путей `/rooms/guest` или `/join/guest`.
И гости, и авторизованные используют единые endpoint-ы.

### 1) Создать комнату

`POST /rooms`

Body (опционально, только для гостя):

```json
{ "username": "Вася" }
```

Поведение:

- Если передан `Authorization: Bearer <access_token>`: создаётся комната авторизованного хоста.
- Если токена нет: создаётся гостевая комната.
- Если у гостя не передан `username`, сервер сгенерирует имя вида `Гость_xxxxxx`.

Ответ:

- Авторизованный: `{ "room_id": "...", "user_id": "..." }`
- Гость: `{ "room_id": "...", "user_id": "...", "username": "..." }`

### 2) Войти в комнату

`POST /rooms/{room_id}/join`

Body (опционально, только для гостя):

```json
{ "username": "Петя" }
```

Ответ:

- Авторизованный: `{ "user_id": "..." }`
- Гость: `{ "user_id": "...", "username": "..." }`

Возможные ошибки:

- `404`: комната не найдена или игра уже началась.

### 3) Запустить игру

`POST /rooms/{room_id}/start`

Права:

- Если хост зарегистрированный, требуется его валидный JWT.
- Если хост гостевой, требуется query-параметр `user_id=<host_user_id>`.

После успешного запуска всем участникам рассылается `GAME_STARTED`.
Сообщение отправляется только участникам с активным WebSocket-подключением.

Возможные ошибки:

- `400`: неверный статус комнаты для запуска.
- `403`: запуск пытается не хост.
- `404`: комната не найдена.

Успешный ответ содержит:

```json
{
	"status": "ok",
	"notified": 1,
	"undelivered_user_ids": []
}
```

### 4) Получить состояние комнаты

`GET /rooms/{room_id}`

Возвращает:

```json
{
	"host_user_id": "...",
	"participants": {
		"<user_id>": {
			"username": "...",
			"connected": true,
			"is_guest": true
		}
	},
	"status": "waiting"
}
```

## События WebSocket

### Клиент -> сервер

Поддерживается только heartbeat-сообщение:

```json
{ "type": "PING" }
```

Если JSON невалидный или формат сообщения неверный, сервер отвечает `ERROR` и не рвёт соединение.

### Сервер -> клиент

`ROOM_STATE`

```json
{
	"type": "ROOM_STATE",
	"payload": {
		"host_user_id": "...",
		"participants": {
			"<user_id>": {
				"username": "...",
				"connected": true,
				"is_guest": false
			}
		},
		"status": "waiting"
	}
}
```

`PLAYER_JOINED`

```json
{
	"type": "PLAYER_JOINED",
	"payload": {
		"user_id": "...",
		"username": "...",
		"is_guest": true
	}
}
```

`PLAYER_DISCONNECTED`

```json
{
	"type": "PLAYER_DISCONNECTED",
	"payload": {
		"user_id": "..."
	}
}
```

`GAME_STARTED`

```json
{
	"type": "GAME_STARTED",
	"payload": {
		"room_id": "..."
	}
}
```

`PONG`

```json
{ "type": "PONG" }
```

`ERROR`

```json
{
	"type": "ERROR",
	"payload": {
		"message": "Невалидный JSON"
	}
}
```

## Жизненный цикл комнаты

```text
1. POST /rooms -> room_id, user_id (хост)
2. POST /rooms/{room_id}/join -> user_id (участник)
3. ws://.../ws/{room_id}/{user_id}?token=... -> подключение
4. POST /rooms/{room_id}/start -> GAME_STARTED
5. disconnect -> PLAYER_DISCONNECTED
```

## TTL-очистка

Фоновая задача в приложении запускается раз в 60 секунд и вызывает очистку комнат.

Комната удаляется, если одновременно выполняются условия:

- все участники офлайн (`connected = false`),
- с момента последней активности прошло более 60 секунд.
