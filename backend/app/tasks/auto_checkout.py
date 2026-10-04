import logging
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.database import async_session_factory
from app.models.booking import Booking, BookingStatus
from app.models.setting import SystemSetting
from app.services import booking_service

logger = logging.getLogger(__name__)


def is_checkout_due(check_out, today, now_time: dt_time, threshold: dt_time) -> bool:
    """判断订单是否应退房：迟于退房日则补跑防漏，当日则达到配置时间后触发。"""
    if check_out < today:
        return True
    if check_out == today:
        return now_time >= threshold
    return False


def _parse_time(value: str) -> dt_time:
    hour, minute = value.split(":")
    return dt_time(int(hour), int(minute))


async def auto_checkout_due_bookings_task() -> None:
    async with async_session_factory() as session:
        try:
            setting = (
                await session.execute(select(SystemSetting).where(SystemSetting.id == 1))
            ).scalar_one_or_none()
            if setting is None or not setting.auto_checkout_enabled:
                return

            try:
                tz = ZoneInfo(setting.timezone)
            except Exception:
                tz = ZoneInfo("Asia/Shanghai")

            now = datetime.now(tz)
            threshold = _parse_time(setting.auto_checkout_time)

            result = await session.execute(
                select(Booking).where(
                    Booking.status == BookingStatus.CHECKED_IN,
                    Booking.check_out <= now.date(),
                )
            )
            due_bookings = result.scalars().all()

            for booking in due_bookings:
                if is_checkout_due(booking.check_out, now.date(), now.time(), threshold):
                    await booking_service.check_out_booking(session, booking.id)
                    logger.info("Auto checked-out booking %s", booking.id)
        except Exception:
            logger.exception("Failed to run auto checkout")