from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database.connection import engine

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
