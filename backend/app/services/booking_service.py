import asyncio
import logging
import random
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.booking import Booking, BookingStatus
from app.models.inventory import DailyRoomInventory, InventoryStatus
from app.models.room import Room, RoomStatus
from app.services import inventory_service
from app.services.transaction import transaction

logger = logging.getLogger(__name__)
settings = get_settings()


async def _load_booking(db: AsyncSession, booking_id: int) -> Booking:
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.room).selectinload(Room.room_type))
        .where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


async def create_hold_booking(
    db: AsyncSession,
    user_id: int,
    room_id: int,
    check_in: date,
    check_out: date,
    idempotency_key: str | None = None,
) -> Booking:
    if check_out <= check_in:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date range")

    # 接口幂等：同一幂等键直接返回已建订单，避免网络重试产生重复预订
    if idempotency_key:
        existing = await _find_booking_by_idempotency_key(db, idempotency_key)
        if existing is not None:
            if existing.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key already used by another user",
                )
            return existing

    required_days = (check_out - check_in).days

    for attempt in range(settings.BOOKING_LOCK_RETRY_TIMES):
        try:
            return await _create_hold_booking_once(
                db, user_id, room_id, check_in, check_out, required_days, idempotency_key
            )
        except inventory_service.InventoryLockError:
            # NOWAIT 锁冲突：指数退避后重试，最后一次失败返回 423
            if attempt == settings.BOOKING_LOCK_RETRY_TIMES - 1:
                break
            backoff_ms = settings.BOOKING_LOCK_RETRY_BASE_MS * (2 ** attempt)
            await asyncio.sleep(backoff_ms / 1000.0 + random.uniform(0, 0.005))
        except IntegrityError:
            # 并发下另一请求已用同一幂等键建单（唯一键兜底），回查并返回既有订单
            if idempotency_key:
                existing = await _find_booking_by_idempotency_key(db, idempotency_key)
                if existing is not None and existing.user_id == user_id:
                    return existing
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate booking request or idempotency key conflict",
            )

    raise HTTPException(
        status_code=status.HTTP_423_LOCKED,
        detail="Room is being booked by another user, please retry later",
    )


async def _create_hold_booking_once(
    db: AsyncSession,
    user_id: int,
    room_id: int,
    check_in: date,
    check_out: date,
    required_days: int,
    idempotency_key: str | None,
) -> Booking:
    try:
        async with transaction(db):
            room_result = await db.execute(
                select(Room).options(selectinload(Room.room_type)).where(Room.id == room_id)
            )
            room = room_result.scalar_one_or_none()
            if not room:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
            if room.status != RoomStatus.ACTIVE:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is not available")

            daily_records = await inventory_service.lock_inventory_for_update(
                db, room_id, check_in, check_out
            )

            if len(daily_records) != required_days:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Some dates in the range are not open for booking",
                )

            for record in daily_records:
                if record.status != InventoryStatus.AVAILABLE:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Room is not available on {record.date}",
                    )

            total_price = room.room_type.base_price * required_days
            booking = Booking(
                user_id=user_id,
                room_id=room_id,
                check_in=check_in,
                check_out=check_out,
                total_price=total_price,
                status=BookingStatus.PENDING,
                idempotency_key=idempotency_key,
            )
            db.add(booking)
            await db.flush()

            held_until = datetime.now(UTC) + timedelta(minutes=settings.HOLD_TTL_MINUTES)
            inventory_service.mark_held(daily_records, booking.id, held_until)
            booking_id = booking.id

        return await _load_booking(db, booking_id)
    except HTTPException:
        raise
    except (inventory_service.InventoryLockError, IntegrityError):
        raise
    except Exception as e:
        logger.error("Failed to create hold booking: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create booking",
        )


async def _find_booking_by_idempotency_key(db: AsyncSession, idempotency_key: str) -> Booking | None:
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.room).selectinload(Room.room_type))
        .where(Booking.idempotency_key == idempotency_key)
    )
    return result.scalar_one_or_none()


async def confirm_booking(db: AsyncSession, booking_id: int) -> Booking:
    async with transaction(db):
        booking = await _get_booking_for_update(db, booking_id)
        if booking.status != BookingStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending bookings can be confirmed",
            )

        records = await inventory_service.get_inventory_for_booking(
            db, booking.room_id, booking.check_in, booking.check_out, booking.id
        )
        if not records:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventory records not found for this booking",
            )

        for record in records:
            if record.status not in (InventoryStatus.HELD, InventoryStatus.BOOKED):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Inventory on {record.date} is not held",
                )

        inventory_service.mark_booked(records)
        booking.status = BookingStatus.CONFIRMED

    return await _load_booking(db, booking_id)


async def cancel_booking(
    db: AsyncSession,
    booking_id: int,
    user_id: int,
    is_admin: bool = False,
) -> None:
    async with transaction(db):
        booking = await _get_booking_for_update(db, booking_id)

        if not is_admin and booking.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        if booking.status in (BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel this booking",
            )

        if booking.status == BookingStatus.CANCELLED:
            return

        records = await inventory_service.get_inventory_for_booking(
            db, booking.room_id, booking.check_in, booking.check_out, booking.id
        )
        if records:
            inventory_service.mark_available(records)

        booking.status = BookingStatus.CANCELLED


async def check_in_booking(db: AsyncSession, booking_id: int) -> Booking:
    async with transaction(db):
        booking = await _get_booking_for_update(db, booking_id)
        if booking.status != BookingStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only confirmed bookings can check in",
            )
        booking.status = BookingStatus.CHECKED_IN

    return await _load_booking(db, booking_id)


async def check_out_booking(db: AsyncSession, booking_id: int) -> Booking:
    async with transaction(db):
        booking = await _get_booking_for_update(db, booking_id)
        if booking.status != BookingStatus.CHECKED_IN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only checked-in bookings can check out",
            )
        booking.status = BookingStatus.CHECKED_OUT

    return await _load_booking(db, booking_id)


async def release_expired_holds(db: AsyncSession) -> int:
    now = datetime.now(UTC)
    result = await db.execute(
        select(DailyRoomInventory).where(
            and_(
                DailyRoomInventory.status == InventoryStatus.HELD,
                DailyRoomInventory.held_until.is_not(None),
                DailyRoomInventory.held_until < now,
            )
        )
    )
    expired_records = list(result.scalars().all())
    if not expired_records:
        return 0

    booking_ids = {r.booking_id for r in expired_records if r.booking_id is not None}
    released = 0

    async with transaction(db):
        for booking_id in booking_ids:
            booking = await _get_booking_for_update(db, booking_id)
            if booking.status != BookingStatus.PENDING:
                continue

            records = await inventory_service.get_inventory_for_booking(
                db, booking.room_id, booking.check_in, booking.check_out, booking.id
            )
            inventory_service.mark_available(records)
            booking.status = BookingStatus.CANCELLED
            released += 1

    return released


async def _get_booking_for_update(db: AsyncSession, booking_id: int) -> Booking:
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking
