from dotenv import load_dotenv
import os

load_dotenv()

# Полная строка подключения — хранится единым значением в .env
DATABASE_URL: str = os.getenv("DATABASE_URL", "")

# Настройки JWT
SECRET_KEY: str = os.getenv("SECRET_KEY", "")
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
# Срок действия refresh-токена в днях
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))