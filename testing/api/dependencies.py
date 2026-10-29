from fastapi import Depends

from ..config import DB_URL, MAIN_API_URL
from ..database import Database
from ..services.fix_client import FixApiClient
from ..services.job_manager import JobManager
from ..services.judge import JudgeService
from ..services.testing_service import TestingService

# Constructed lazily so tests can override get_testing_service without
# touching the real database.
_DB: Database | None = None
_SERVICE: TestingService | None = None
_FIX_CLIENT: FixApiClient | None = None
_JUDGE: JudgeService | None = None

# One per process: enforces a single test running at a time.
JOB_MANAGER: JobManager = JobManager()


def get_db() -> Database:
    global _DB
    if _DB is None:
        _DB = Database(DB_URL)
    return _DB


def get_fix_client() -> FixApiClient:
    global _FIX_CLIENT
    if _FIX_CLIENT is None:
        _FIX_CLIENT = FixApiClient(MAIN_API_URL)
    return _FIX_CLIENT


def get_judge() -> JudgeService:
    global _JUDGE
    if _JUDGE is None:
        _JUDGE = JudgeService()
    return _JUDGE


def get_job_manager() -> JobManager:
    return JOB_MANAGER


def get_testing_service(
    fix_client: FixApiClient = Depends(get_fix_client),
    judge: JudgeService = Depends(get_judge),
) -> TestingService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = TestingService(get_db(), fix_client, judge)
    return _SERVICE
