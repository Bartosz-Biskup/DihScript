import os
from typing import Final

from dotenv import load_dotenv

load_dotenv()

DB_URL: Final[str] = os.getenv("DATABASE_URL", "sqlite:///./app.db")
CORS_ORIGINS: Final[list[str]] = [
    origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()
]
