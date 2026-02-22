"""Database session management"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import async_session

async_session_factory = async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
