"""定时任务测试：自动退房与过期 Hold 释放。"""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.database import async_session_factory
from app.models.booking import Booking, BookingStatus
from app.models.inventory import DailyRoomInventory, InventoryStatus
from app.models.room import Room
from app.models.setting import SystemSetting
from app.models.user import User
from app.tasks.auto_checkout import auto_checkout_due_bookings_task, is_checkout_due
from app.tasks.hold_release import release_expired_holds_task
from tests.conftest import register_and_login


async def test_is_checkout_due_pure():
    today = date(2026, 1, 1)
    threshold = time(12, 0)
    # 迟于退房日 → 补跑防漏
    assert is_checkout_due(today - timedelta(days=1), today, time(8, 0), threshold) is True
    # 当日未到配置时间 → 不触发
    assert is_checkout_due(today, today, time(8, 0), threshold) is False
    # 当日达到配置时间 → 触发
    assert is_checkout_due(today, today, time(13, 0), threshold) is True
    # 未到退房日 → 不触发
    assert is_checkout_due(today + timedelta(days=1), today, time(13, 0), threshold) is False


async def _set_auto_checkout(enabled: bool, trigger_time: str = "00:00"):
    async with async_session_factory() as session:
        session.add(
            SystemSetting(
                id=1,
                auto_checkout_enabled=enabled,
                auto_checkout_time=trigger_time,
                timezone="Asia/Shanghai",
            )
        )
        await session.commit()


async def _make_checked_in_booking(username: str, check_out: date) -> int:
    async with async_session_factory() as session:
        user_id = (
            await session.execute(select(User.id).where(User.username == username))
        ).scalar_one()
        room_id = (await session.execute(select(Room.id).limit(1))).scalar_one()
        booking = Booking(
            user_id=user_id,
            room_id=room_id,
            check_in=check_out - timedelta(days=2),
            check_out=check_out,
            total_price=Decimal("299.00"),
            status=BookingStatus.CHECKED_IN,
        )
        session.add(booking)
        await session.commit()
        return booking.id


async def test_auto_checkout_checks_out_due_booking(client):
    await register_and_login(client, "autocheck_user")
    booking_id = await _make_checked_in_booking("autocheck_user", date.today())
    await _set_auto_checkout(True)

    await auto_checkout_due_bookings_task()

    async with async_session_factory() as session:
        booking = await session.get(Booking, booking_id)
        assert booking.status == BookingStatus.CHECKED_OUT


async def test_auto_checkout_disabled_skips(client):
    await register_and_login(client, "noautocheck_user")
    booking_id = await _make_checked_in_booking("noautocheck_user", date.today())
    await _set_auto_checkout(False)

    await auto_checkout_due_bookings_task()

    async with async_session_factory() as session:
        booking = await session.get(Booking, booking_id)
        assert booking.status == BookingStatus.CHECKED_IN


async def test_release_expired_holds_cancels_pending(client):
    await register_and_login(client, "holdrel_user")
    today = date.today()
    check_in = today + timedelta(days=1)
    check_out = today + timedelta(days=3)

    async with async_session_factory() as session:
        user_id = (
            await session.execute(select(User.id).where(User.username == "holdrel_user"))
        ).scalar_one()
        room_id = (await session.execute(select(Room.id).limit(1))).scalar_one()
        booking = Booking(
            user_id=user_id,
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            total_price=Decimal("299.00"),
            status=BookingStatus.PENDING,
        )
        session.add(booking)
        await session.flush()
        for d in (check_in, check_in + timedelta(days=1)):
            inventory = (
                await session.execute(
                    select(DailyRoomInventory).where(
                        DailyRoomInventory.room_id == room_id,
                        DailyRoomInventory.date == d,
                    )
                )
            ).scalar_one()
            inventory.status = InventoryStatus.HELD
            inventory.booking_id = booking.id
            inventory.held_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        await session.commit()
        booking_id = booking.id

    await release_expired_holds_task()

    async with async_session_factory() as session:
        booking = await session.get(Booking, booking_id)
        assert booking.status == BookingStatus.CANCELLED
        inventories = (
            await session.execute(
                select(DailyRoomInventory).where(
                    DailyRoomInventory.room_id == booking.room_id,
                    DailyRoomInventory.date >= booking.check_in,
                    DailyRoomInventory.date < booking.check_out,
                )
            )
        ).scalars().all()
        assert inventories and all(
            i.status == InventoryStatus.AVAILABLE for i in inventories
        )
