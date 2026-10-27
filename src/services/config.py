import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

load_dotenv()

MODEL: Final[str] = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
PROMPTS_DIR: Final[Path] = Path(os.getenv("PROMPTS_DIR", "prompts"))
