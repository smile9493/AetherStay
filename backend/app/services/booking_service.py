import logging
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import and_, select
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
) -> Booking:
    if check_out <= check_in:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date range")

    required_days = (check_out - check_in).days

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

            try:
                daily_records = await inventory_service.lock_inventory_for_update(
                    db, room_id, check_in, check_out
                )
            except inventory_service.InventoryLockError:
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Room is being booked by another user, please retry later",
                )

            if len(daily_records) != required_days:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Some dates in the range are not open for booking",
                )

            now = datetime.now(UTC).replace(tzinfo=None)
            for record in daily_records:
                if inventory_service.is_bookable(record, now):
                    if record.status == InventoryStatus.HELD:
                        # Expired hold — release it within the same transaction
                        inventory_service.mark_available([record])
                elif inventory_service.is_held_valid(record, now):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Room is held by another user on {record.date}",
                    )
                else:
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
            )
            db.add(booking)
            await db.flush()

            held_until = datetime.now(UTC) + timedelta(minutes=settings.HOLD_TTL_MINUTES)
            inventory_service.mark_held(daily_records, booking.id, held_until)
            booking_id = booking.id

        return await _load_booking(db, booking_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create hold booking: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create booking",
        )


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

        now = datetime.now(UTC).replace(tzinfo=None)
        expected_days = inventory_service.required_days(booking.check_in, booking.check_out)

        # All failure modes (missing records, not HELD, expired) → 400 Hold expired
        if len(records) != expected_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hold has expired, please create a new booking",
            )

        for record in records:
            if record.status != InventoryStatus.HELD:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Hold has expired, please create a new booking",
                )
            if record.held_until is None or record.held_until < now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Hold has expired, please create a new booking",
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
    now = datetime.now(UTC).replace(tzinfo=None)
    released = 0

    async with transaction(db):
        result = await db.execute(
            select(DailyRoomInventory)
            .where(
                and_(
                    DailyRoomInventory.status == InventoryStatus.HELD,
                    DailyRoomInventory.held_until.is_not(None),
                    DailyRoomInventory.held_until < now,
                )
            )
            .with_for_update()
        )
        expired_records = list(result.scalars().all())
        if not expired_records:
            return 0

        # Group by booking_id
        booking_map: dict[int | None, list[DailyRoomInventory]] = {}
        for r in expired_records:
            bid = r.booking_id
            if bid not in booking_map:
                booking_map[bid] = []
            booking_map[bid].append(r)

        for booking_id, records in booking_map.items():
            # Get ALL inventory for the booking (not just expired rows)
            if booking_id is not None:
                booking = await _get_booking_for_update(db, booking_id)
                all_records = await inventory_service.get_inventory_for_booking(
                    db, booking.room_id, booking.check_in, booking.check_out, booking.id
                )
            else:
                all_records = records

            inventory_service.mark_available(all_records)
            released += 1

            if booking_id is not None and booking.status == BookingStatus.PENDING:
                booking.status = BookingStatus.CANCELLED

    return released


async def _get_booking_for_update(db: AsyncSession, booking_id: int) -> Booking:
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking
