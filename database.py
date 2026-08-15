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
    ForeignKey
)

from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    relationship
)


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing")


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


Base = declarative_base()


class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True
    )

    telegram_user_id = Column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True
    )

    username = Column(
        Text,
        nullable=True
    )

    first_name = Column(
        Text,
        nullable=True
    )

    last_name = Column(
        Text,
        nullable=True
    )

    language = Column(
        Text,
        nullable=False,
        default="en"
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    last_seen = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Conversation(Base):

    __tablename__ = "conversations"

    id = Column(
        Integer,
        primary_key=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    role = Column(
        Text,
        nullable=False
    )

    message = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    user = relationship(
        "User",
        back_populates="conversations"
    )


Base.metadata.create_all(engine)