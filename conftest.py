import pytest
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# Keep the testing tool's own database away from the real one during tests.
os.environ.setdefault(
    "TESTING_DB_URL",
    f"sqlite:///{tempfile.mkdtemp(prefix='testing_tool_')}/testing.db",
)


from api.rate_limiter import limiter

@pytest.fixture(autouse=True)
def reset_limiter():
    limiter.reset()
