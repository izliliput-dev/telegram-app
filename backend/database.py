from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./storage/users.db")

# Синхронный engine только для создания таблиц
sync_engine = create_engine(DATABASE_URL.replace("aiosqlite", "sqlite"))

# Асинхронный engine для работы с данными
engine = create_async_engine(DATABASE_URL)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()
