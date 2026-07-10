"""Core booking service tests — Hold-then-Confirm state machine."""

from __future__ import annotations

import os

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_aetherstay.db")

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import and_, select

from app.database import async_session_factory
from app.models.booking import Booking, BookingStatus
from app.models.inventory import DailyRoomInventory, InventoryStatus
from app.models.room import Room, RoomStatus
from app.models.user import User
from app.services import booking_service, inventory_service
from app.utils.auth import hash_password

# Skip concurrent lock test on SQLite (no real row-level locking)
_HAS_REAL_FOR_UPDATE = os.environ.get("DATABASE_URL", "").startswith("mysql")


async def _find_available_slot() -> tuple[Room, date, date]:
    async with async_session_factory() as db:
        rooms = (
            await db.execute(select(Room).where(Room.status == RoomStatus.ACTIVE))
        ).scalars().all()
        for room in rooms:
            for offset in range(10, 80, 2):
                check_in = date.today() + timedelta(days=offset)
                check_out = check_in + timedelta(days=2)
                records = (
                    await db.execute(
                        select(DailyRoomInventory).where(
                            and_(
                                DailyRoomInventory.room_id == room.id,
                                DailyRoomInventory.date >= check_in,
                                DailyRoomInventory.date < check_out,
                            )
                        )
                    )
                ).scalars().all()
                if len(records) == 2 and all(r.status == InventoryStatus.AVAILABLE for r in records):
                    return room, check_in, check_out
    pytest.skip("No available inventory slot found in seed data window")


async def _create_user(db) -> User:
    user = User(
        username=f"pytest_{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("testpass123"),
    )
    db.add(user)
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_create_hold_booking_success():
    room, check_in, check_out = await _find_available_slot()
    async with async_session_factory() as db:
        user = await _create_user(db)
        await db.commit()
        booking = await booking_service.create_hold_booking(
            db, user_id=user.id, room_id=room.id, check_in=check_in, check_out=check_out
        )
        assert booking.status == BookingStatus.PENDING
        records = await inventory_service.get_inventory_for_booking(
            db, room.id, check_in, check_out, booking.id
        )
        assert len(records) == 2
        assert all(r.status == InventoryStatus.HELD for r in records)
        assert all(r.held_until is not None for r in records)


@pytest.mark.asyncio
async def test_create_hold_conflict():
    room, check_in, check_out = await _find_available_slot()
    async with async_session_factory() as db:
        user1 = await _create_user(db)
        user2 = await _create_user(db)
        await db.commit()
        await booking_service.create_hold_booking(
            db, user_id=user1.id, room_id=room.id, check_in=check_in, check_out=check_out
        )
        with pytest.raises(HTTPException) as exc:
            await booking_service.create_hold_booking(
                db, user_id=user2.id, room_id=room.id, check_in=check_in, check_out=check_out
            )
        assert exc.value.status_code in (409, 423)


@pytest.mark.asyncio
async def test_confirm_booking():
    room, check_in, check_out = await _find_available_slot()
    async with async_session_factory() as db:
        user = await _create_user(db)
        await db.commit()
        booking = await booking_service.create_hold_booking(
            db, user_id=user.id, room_id=room.id, check_in=check_in, check_out=check_out
        )
        confirmed = await booking_service.confirm_booking(db, booking.id)
        assert confirmed.status == BookingStatus.CONFIRMED
        records = await inventory_service.get_inventory_for_booking(
            db, room.id, check_in, check_out, booking.id
        )
        assert all(r.status == InventoryStatus.BOOKED for r in records)


@pytest.mark.asyncio
async def test_confirm_expired_hold():
    room, check_in, check_out = await _find_available_slot()
    async with async_session_factory() as db:
        user = await _create_user(db)
        await db.commit()
        booking = await booking_service.create_hold_booking(
            db, user_id=user.id, room_id=room.id, check_in=check_in, check_out=check_out
        )
        records = await inventory_service.get_inventory_for_booking(
            db, room.id, check_in, check_out, booking.id
        )
        past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
        for r in records:
            r.held_until = past
        await db.commit()

        with pytest.raises(HTTPException) as exc:
            await booking_service.confirm_booking(db, booking.id)
        assert exc.value.status_code == 400
        assert "expired" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_cancel_releases_inventory():
    room, check_in, check_out = await _find_available_slot()
    async with async_session_factory() as db:
        user = await _create_user(db)
        await db.commit()
        booking = await booking_service.create_hold_booking(
            db, user_id=user.id, room_id=room.id, check_in=check_in, check_out=check_out
        )
        await booking_service.cancel_booking(
            db, booking.id, user_id=user.id, is_admin=False
        )
        result = await db.execute(select(Booking).where(Booking.id == booking.id))
        assert result.scalar_one().status == BookingStatus.CANCELLED
        records = await inventory_service.get_inventory_for_booking(
            db, room.id, check_in, check_out
        )
        for r in records:
            if check_in <= r.date < check_out:
                assert r.status == InventoryStatus.AVAILABLE


@pytest.mark.asyncio
async def test_release_expired_holds():
    room, check_in, check_out = await _find_available_slot()
    async with async_session_factory() as db:
        user = await _create_user(db)
        await db.commit()
        booking = await booking_service.create_hold_booking(
            db, user_id=user.id, room_id=room.id, check_in=check_in, check_out=check_out
        )
        records = await inventory_service.get_inventory_for_booking(
            db, room.id, check_in, check_out, booking.id
        )
        past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
        for r in records:
            r.held_until = past
        await db.commit()

        released = await booking_service.release_expired_holds(db)
        assert released >= len(records)
        result = await db.execute(select(Booking).where(Booking.id == booking.id))
        assert result.scalar_one().status == BookingStatus.CANCELLED


@pytest.mark.asyncio
async def test_serialize_booking_includes_held_until():
    room, check_in, check_out = await _find_available_slot()
    async with async_session_factory() as db:
        user = await _create_user(db)
        await db.commit()
        booking = await booking_service.create_hold_booking(
            db, user_id=user.id, room_id=room.id, check_in=check_in, check_out=check_out
        )
        response = await booking_service.serialize_booking(db, booking)
        assert response.held_until is not None


@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_REAL_FOR_UPDATE, reason="Requires MySQL FOR UPDATE NOWAIT for true concurrent locking")
async def test_concurrent_hold_only_one_succeeds():
    room, check_in, check_out = await _find_available_slot()

    async def attempt(idx: int):
        async with async_session_factory() as session:
            user = User(
                username=f"conc_{idx}_{uuid.uuid4().hex[:6]}",
                password_hash=hash_password("testpass123"),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            try:
                await booking_service.create_hold_booking(
                    session,
                    user_id=user.id,
                    room_id=room.id,
                    check_in=check_in,
                    check_out=check_out,
                )
                await session.commit()
                return "ok"
            except HTTPException as e:
                await session.rollback()
                return e.status_code

    results = await asyncio.gather(attempt(1), attempt(2))
    ok_count = sum(1 for r in results if r == "ok")
    assert ok_count == 1


@pytest.mark.asyncio
async def test_create_hold_booking_invalid_dates():
    """Invalid date range (check_out <= check_in) should raise 400."""
    room, _, _ = await _find_available_slot()
    async with async_session_factory() as db:
        user = await _create_user(db)
        await db.commit()
        check_in = date.today() + timedelta(days=30)
        check_out = check_in  # same day → invalid
        with pytest.raises(HTTPException) as exc:
            await booking_service.create_hold_booking(
                db, user_id=user.id, room_id=room.id,
                check_in=check_in, check_out=check_out,
            )
        assert exc.value.status_code == 400
        assert "Invalid" in exc.value.detail or "invalid" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_create_hold_booking_expired_hold_reused():
    """Expired hold should be cleared and room re-bookable by another user."""
    room, check_in, check_out = await _find_available_slot()
    async with async_session_factory() as db:
        user1 = await _create_user(db)
        await db.commit()
        booking1 = await booking_service.create_hold_booking(
            db, user_id=user1.id, room_id=room.id,
            check_in=check_in, check_out=check_out,
        )
        # Expire the hold
        records = await inventory_service.get_inventory_for_booking(
            db, room.id, check_in, check_out, booking1.id
        )
        past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
        for r in records:
            r.held_until = past
        await db.commit()

        # Second user should be able to book (expired hold auto-released)
        user2 = await _create_user(db)
        await db.commit()
        booking2 = await booking_service.create_hold_booking(
            db, user_id=user2.id, room_id=room.id,
            check_in=check_in, check_out=check_out,
        )
        assert booking2.status == BookingStatus.PENDING
        assert booking2.user_id == user2.id


@pytest.mark.asyncio
async def test_cancel_booking_already_checked_in():
    """Checked-in booking cannot be cancelled."""
    room, check_in, check_out = await _find_available_slot()
    async with async_session_factory() as db:
        user = await _create_user(db)
        await db.commit()
        user_id = user.id  # capture before entering transaction contexts
        booking = await booking_service.create_hold_booking(
            db, user_id=user_id, room_id=room.id,
            check_in=check_in, check_out=check_out,
        )
        confirmed = await booking_service.confirm_booking(db, booking.id)
        checked_in = await booking_service.check_in_booking(db, confirmed.id)
        assert checked_in.status == BookingStatus.CHECKED_IN

        with pytest.raises(HTTPException) as exc:
            await booking_service.cancel_booking(
                db, checked_in.id, user_id=user_id, is_admin=False
            )
        assert exc.value.status_code == 400
        assert "Cannot cancel" in exc.value.detail or "cannot cancel" in exc.value.detail.lower()
