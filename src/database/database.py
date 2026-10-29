from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class Database:
    def __init__(self, url: str) -> None:
        if url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            engine_kwargs = {"connect_args": connect_args}
        else:
            # MySQL: verify stale pooled connections so the app survives a DB restart.
            engine_kwargs = {"pool_pre_ping": True}
        self.engine = create_engine(url, **engine_kwargs)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

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
