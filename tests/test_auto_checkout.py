"""Auto checkout scheduler and settings tests."""

from __future__ import annotations

import os

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_aetherstay.db")

import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.database import async_session_factory
from app.models.booking import Booking, BookingStatus
from app.models.room import Room, RoomStatus
from app.models.user import User
from app.services import booking_service, settings_service
from app.services.booking_service import is_checkout_due
from app.utils.auth import hash_password
from test_booking_service import _find_available_slot


async def _create_user(db) -> User:
    user = User(
        username=f"pytest_{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("testpass123"),
    )
    db.add(user)
    await db.flush()
    return user


async def _create_checked_in_booking(check_out: date | None = None) -> Booking:
    room, check_in, default_check_out = await _find_available_slot()
    target_check_out = check_out or default_check_out
    async with async_session_factory() as db:
        user = await _create_user(db)
        await db.commit()
        booking = await booking_service.create_hold_booking(
            db,
            user_id=user.id,
            room_id=room.id,
            check_in=check_in,
            check_out=default_check_out,
        )
        await booking_service.confirm_booking(db, booking.id)
        booking = await booking_service.check_in_booking(db, booking.id)

    if target_check_out != default_check_out:
        async with async_session_factory() as db:
            result = await db.execute(select(Booking).where(Booking.id == booking.id))
            row = result.scalar_one()
            row.check_out = target_check_out
            await db.commit()
            await db.refresh(row)
            return row
    return booking


def test_is_checkout_due_past_date():
    tz = "Asia/Shanghai"
    now = datetime(2026, 7, 10, 10, 0, tzinfo=ZoneInfo(tz))
    assert is_checkout_due(date(2026, 7, 9), now, "12:00", tz)


def test_is_checkout_due_today_before_time():
    tz = "Asia/Shanghai"
    now = datetime(2026, 7, 10, 11, 59, tzinfo=ZoneInfo(tz))
    assert not is_checkout_due(date(2026, 7, 10), now, "12:00", tz)


def test_is_checkout_due_today_after_time():
    tz = "Asia/Shanghai"
    now = datetime(2026, 7, 10, 12, 1, tzinfo=ZoneInfo(tz))
    assert is_checkout_due(date(2026, 7, 10), now, "12:00", tz)


@pytest.mark.asyncio
async def test_auto_checkout_yesterday():
    yesterday = date.today() - timedelta(days=1)
    booking = await _create_checked_in_booking(check_out=yesterday)
    now = datetime.now(UTC)

    async with async_session_factory() as db:
        count = await booking_service.auto_checkout_due_bookings(
            db,
            now=now,
            checkout_time="12:00",
            timezone_name="Asia/Shanghai",
        )
        assert count >= 1
        result = await db.execute(select(Booking).where(Booking.id == booking.id))
        assert result.scalar_one().status == BookingStatus.CHECKED_OUT


@pytest.mark.asyncio
async def test_auto_checkout_today_before_time_unchanged():
    today = date.today()
    booking = await _create_checked_in_booking(check_out=today)
    tz = ZoneInfo("Asia/Shanghai")
    now = datetime.now(tz).replace(hour=9, minute=0, second=0, microsecond=0)

    async with async_session_factory() as db:
        await booking_service.auto_checkout_due_bookings(
            db,
            now=now,
            checkout_time="12:00",
            timezone_name="Asia/Shanghai",
        )
        result = await db.execute(select(Booking).where(Booking.id == booking.id))
        assert result.scalar_one().status == BookingStatus.CHECKED_IN


@pytest.mark.asyncio
async def test_auto_checkout_today_after_time():
    today = date.today()
    booking = await _create_checked_in_booking(check_out=today)
    tz = ZoneInfo("Asia/Shanghai")
    now = datetime.now(tz).replace(hour=14, minute=0, second=0, microsecond=0)

    async with async_session_factory() as db:
        count = await booking_service.auto_checkout_due_bookings(
            db,
            now=now,
            checkout_time="12:00",
            timezone_name="Asia/Shanghai",
        )
        assert count >= 1
        result = await db.execute(select(Booking).where(Booking.id == booking.id))
        assert result.scalar_one().status == BookingStatus.CHECKED_OUT


@pytest.mark.asyncio
async def test_auto_checkout_skips_confirmed():
    room, check_in, check_out = await _find_available_slot()
    past_check_out = date.today() - timedelta(days=1)
    async with async_session_factory() as db:
        user = await _create_user(db)
        await db.commit()
        booking = await booking_service.create_hold_booking(
            db,
            user_id=user.id,
            room_id=room.id,
            check_in=check_in,
            check_out=check_out,
        )
        await booking_service.confirm_booking(db, booking.id)
        result = await db.execute(select(Booking).where(Booking.id == booking.id))
        row = result.scalar_one()
        row.check_out = past_check_out
        await db.commit()
        booking_id = row.id

    async with async_session_factory() as db:
        await booking_service.auto_checkout_due_bookings(
            db,
            now=datetime.now(UTC),
            checkout_time="12:00",
            timezone_name="Asia/Shanghai",
        )
        result = await db.execute(select(Booking).where(Booking.id == booking_id))
        assert result.scalar_one().status == BookingStatus.CONFIRMED


@pytest.mark.asyncio
async def test_get_auto_checkout_settings_defaults():
    async with async_session_factory() as db:
        settings = await settings_service.get_auto_checkout_settings(db)
        assert settings.enabled is True
        assert settings.checkout_time == "12:00"
        assert settings.timezone == "Asia/Shanghai"


@pytest.mark.asyncio
async def test_update_auto_checkout_settings():
    async with async_session_factory() as db:
        updated = await settings_service.update_auto_checkout_settings(
            db, enabled=False, checkout_time="14:30", timezone="Asia/Shanghai"
        )
        assert updated.enabled is False
        assert updated.checkout_time == "14:30"

        restored = await settings_service.update_auto_checkout_settings(
            db, enabled=True, checkout_time="12:00", timezone="Asia/Shanghai"
        )
        assert restored.enabled is True
        assert restored.checkout_time == "12:00"


@pytest.mark.asyncio
async def test_admin_get_auto_checkout_settings(admin_client):
    resp = await admin_client.get("/api/v1/admin/settings/auto-checkout")
    assert resp.status_code == 200
    data = resp.json()
    assert "enabled" in data
    assert "checkout_time" in data
    assert data["timezone"] == "Asia/Shanghai"


@pytest.mark.asyncio
async def test_admin_put_auto_checkout_settings(admin_client):
    resp = await admin_client.put(
        "/api/v1/admin/settings/auto-checkout",
        json={"enabled": True, "checkout_time": "13:00", "timezone": "Asia/Shanghai"},
    )
    assert resp.status_code == 200
    assert resp.json()["checkout_time"] == "13:00"

    await admin_client.put(
        "/api/v1/admin/settings/auto-checkout",
        json={"enabled": True, "checkout_time": "12:00", "timezone": "Asia/Shanghai"},
    )


@pytest.mark.asyncio
async def test_admin_put_invalid_checkout_time(admin_client):
    resp = await admin_client.put(
        "/api/v1/admin/settings/auto-checkout",
        json={"enabled": True, "checkout_time": "25:00", "timezone": "Asia/Shanghai"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_settings_forbidden_for_customer(auth_client):
    resp = await auth_client.get("/api/v1/admin/settings/auto-checkout")
    assert resp.status_code == 403
