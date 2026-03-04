from dotenv import load_dotenv
import os

load_dotenv()

# Full connection string — stored as a single value in .env
DATABASE_URL: str = os.getenv("DATABASE_URL", "")

# JWT configuration
SECRET_KEY: str = os.getenv("SECRET_KEY", "")
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))