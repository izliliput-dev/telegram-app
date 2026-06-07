from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./storage/users.db")

# Синхронный engine для создания таблиц
sync_engine = create_engine(
    DATABASE_URL.replace("aiosqlite", "sqlite"),
    connect_args={"check_same_thread": False},
    poolclass=NullPool if "sqlite" in DATABASE_URL else None
)

# Асинхронный engine для работы с данными
async_engine = create_async_engine(DATABASE_URL)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()
