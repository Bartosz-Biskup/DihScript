from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .tables import Base, GroupTable, TestRunTable


class Database:
    def __init__(self, url: str) -> None:
        if url.startswith("sqlite:///") and ":memory:" not in url:
            path = Path(url.removeprefix("sqlite:///"))
            path.parent.mkdir(parents=True, exist_ok=True)

        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, connect_args=connect_args)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    def reset_running(self) -> None:
        """Recover from a crash: return running groups and their runs to pending."""
        with self.session_scope() as session:
            for group in session.query(GroupTable).filter(GroupTable.status == "running"):
                group.status = "pending"
            for run in session.query(TestRunTable).filter(TestRunTable.status == "running"):
                run.status = "pending"

    @contextmanager
    def session_scope(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
