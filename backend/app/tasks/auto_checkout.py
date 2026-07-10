import logging

from app.database import async_session_factory
from app.services import booking_service, settings_service

logger = logging.getLogger(__name__)


async def auto_checkout_task() -> None:
    async with async_session_factory() as session:
        try:
            settings = await settings_service.get_auto_checkout_settings(session)
            if not settings.enabled:
                return
            count = await booking_service.auto_checkout_due_bookings(
                session,
                checkout_time=settings.checkout_time,
                timezone_name=settings.timezone,
            )
            if count:
                logger.info("Auto checkout task processed %d booking(s)", count)
        except Exception:
            logger.exception("Failed to run auto checkout task")
