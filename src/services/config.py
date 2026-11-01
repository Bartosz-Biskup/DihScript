import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

load_dotenv()

# The OpenAI SDK (pointed at DeepSeek) takes plain model names like
# "deepseek-chat". A legacy litellm-style "provider/model" value still works:
# the provider prefix is stripped.
MODEL: Final[str] = os.getenv("LLM_MODEL", "deepseek-chat").rsplit("/", 1)[-1]
PROMPTS_DIR: Final[Path] = Path(os.getenv("PROMPTS_DIR", "prompts"))
