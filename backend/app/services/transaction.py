from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def transaction(db: AsyncSession):
    """Start a clean transaction, rolling back any implicit one from prior Depends calls."""
    if db.in_transaction():
        await db.rollback()
    async with db.begin():
        yield
