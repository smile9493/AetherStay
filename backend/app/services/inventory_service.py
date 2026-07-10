from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import DailyRoomInventory, InventoryStatus


class InventoryLockError(Exception):
    """Raised when NOWAIT lock cannot be acquired."""

    pass


async def lock_inventory_for_update(
    db: AsyncSession,
    room_id: int,
    check_in: date,
    check_out: date,
) -> list[DailyRoomInventory]:
    stmt = (
        select(DailyRoomInventory)
        .where(
            and_(
                DailyRoomInventory.room_id == room_id,
                DailyRoomInventory.date >= check_in,
                DailyRoomInventory.date < check_out,
            )
        )
        .with_for_update(nowait=True)
    )
    try:
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except OperationalError as e:
        if "3572" in str(e.orig) or "Lock wait timeout" in str(e):
            raise InventoryLockError("Room is being booked by another user") from e
        raise


def mark_held(
    records: list[DailyRoomInventory],
    booking_id: int,
    held_until: datetime,
) -> None:
    for record in records:
        record.status = InventoryStatus.HELD
        record.booking_id = booking_id
        record.held_until = held_until


def mark_booked(records: list[DailyRoomInventory]) -> None:
    for record in records:
        record.status = InventoryStatus.BOOKED
        record.held_until = None


def mark_available(records: list[DailyRoomInventory]) -> None:
    for record in records:
        record.status = InventoryStatus.AVAILABLE
        record.booking_id = None
        record.held_until = None


def is_bookable(record: DailyRoomInventory, now: datetime) -> bool:
    """Check if record is bookable: available, or held but expired."""
    if record.status == InventoryStatus.AVAILABLE:
        return True
    if record.status == InventoryStatus.HELD:
        if record.held_until is not None and record.held_until < now:
            return True
    return False


def is_held_valid(record: DailyRoomInventory, now: datetime) -> bool:
    """Check if record has a valid (non-expired) hold."""
    return (
        record.status == InventoryStatus.HELD
        and record.held_until is not None
        and record.held_until >= now
        or False
    )


def required_days(check_in: date, check_out: date) -> int:
    """Calculate number of days in a booking range."""
    return (check_out - check_in).days


async def get_inventory_for_booking(
    db: AsyncSession,
    room_id: int,
    check_in: date,
    check_out: date,
    booking_id: int | None = None,
) -> list[DailyRoomInventory]:
    conditions = [
        DailyRoomInventory.room_id == room_id,
        DailyRoomInventory.date >= check_in,
        DailyRoomInventory.date < check_out,
    ]
    if booking_id is not None:
        conditions.append(DailyRoomInventory.booking_id == booking_id)
    result = await db.execute(select(DailyRoomInventory).where(and_(*conditions)))
    return list(result.scalars().all())


async def generate_inventory_for_room(
    db: AsyncSession,
    room_id: int,
    days: int = 90,
) -> None:
    today = datetime.now(UTC).date()
    for offset in range(days):
        inv_date = today + timedelta(days=offset)
        db.add(
            DailyRoomInventory(
                room_id=room_id,
                date=inv_date,
                status=InventoryStatus.AVAILABLE,
            )
        )
