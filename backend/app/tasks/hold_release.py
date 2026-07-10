import logging

from app.database import async_session_factory
from app.services import booking_service

logger = logging.getLogger(__name__)


async def release_expired_holds_task() -> None:
    async with async_session_factory() as session:
        try:
            released = await booking_service.release_expired_holds(session)
            if released:
                logger.info("Released %d expired hold(s)", released)
        except Exception:
            logger.exception("Failed to release expired holds")
