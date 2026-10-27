from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from database.database import Database
from repositories.subscriber_repository import SubscriberRepository
from services.fix_script_service import FixScriptService
from services.llm_service import LLMService
from services.prompt_fixer_service import PromptFixerService
from services.subscriber_service import SubscriberService

from .config import DB_URL

DB: Database = Database(url=DB_URL)


def get_db() -> Generator[Session, None, None]:
    with DB.session_scope() as session:
        yield session


def get_subscriber_service(session: Session = Depends(get_db)) -> SubscriberService:
    return SubscriberService(SubscriberRepository(session))


def get_prompt_fixer_service() -> PromptFixerService:
    return PromptFixerService(LLMService())


def get_fix_script_service(
    fixer: PromptFixerService = Depends(get_prompt_fixer_service),
    subscribers: SubscriberService = Depends(get_subscriber_service),
) -> FixScriptService:
    return FixScriptService(fixer, subscribers)
