from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    ...


class SubscriberTable(Base):
    __tablename__ = "subscribers"

    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
