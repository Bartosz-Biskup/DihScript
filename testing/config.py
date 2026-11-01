import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

load_dotenv()

PACKAGE_DIR: Final[Path] = Path(__file__).resolve().parent
DATA_DIR: Final[Path] = Path(os.getenv("TESTING_DATA_DIR", str(PACKAGE_DIR / "data")))
PROMPTS_DIR: Final[Path] = Path(os.getenv("TESTING_PROMPTS_DIR", str(PACKAGE_DIR / "prompts")))
STATIC_DIR: Final[Path] = PACKAGE_DIR / "static"

MAIN_API_URL: Final[str] = os.getenv("MAIN_API_URL", "http://127.0.0.1:8000")
JUDGE_MODEL: Final[str] = (
    os.getenv("JUDGE_MODEL") or os.getenv("LLM_MODEL") or "deepseek-chat"
).rsplit("/", 1)[-1]
DB_URL: Final[str] = os.getenv("TESTING_DB_URL") or f"sqlite:///{DATA_DIR / 'testing.db'}"

# Maximum number of inputs accepted in one automatic group.
MAX_GROUP_ITEMS: Final[int] = 1000
