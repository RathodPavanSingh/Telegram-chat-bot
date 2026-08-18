import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    Text,
    DateTime,
)
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    telegram_user_id = Column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )

    username = Column(Text)
    first_name = Column(Text)
    last_name = Column(Text)

    language = Column(
        Text,
        nullable=False,
        default="en",
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    last_seen = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)

    telegram_user_id = Column(
        BigInteger,
        nullable=False,
        index=True,
    )

    role = Column(
        Text,
        nullable=False,
    )

    message = Column(
        Text,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )


Base.metadata.create_all(engine)