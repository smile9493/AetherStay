from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.inventory import DailyRoomInventory, InventoryStatus
from app.models.room import Room, RoomStatus
from app.schemas.room import RoomResponse

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("/search", response_model=list[RoomResponse], operation_id="get_available_rooms")
async def search_rooms(
    check_in: Annotated[date, Query(description="Check-in date")],
    check_out: Annotated[date, Query(description="Check-out date")],
    room_type_id: int | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """Search available rooms for a date range."""
    required_days = (check_out - check_in).days
    if required_days <= 0:
        return []

    now = datetime.now(UTC).replace(tzinfo=None)
    subq = (
        select(DailyRoomInventory.room_id)
        .where(
            and_(
                DailyRoomInventory.date >= check_in,
                DailyRoomInventory.date < check_out,
                or_(
                    DailyRoomInventory.status == InventoryStatus.AVAILABLE,
                    and_(
                        DailyRoomInventory.status == InventoryStatus.HELD,
                        DailyRoomInventory.held_until.is_not(None),
                        DailyRoomInventory.held_until < now,
                    ),
                ),
            )
        )
        .group_by(DailyRoomInventory.room_id)
        .having(func.count() == required_days)
        .subquery()
    )

    stmt = (
        select(Room)
        .options(selectinload(Room.room_type))
        .where(Room.status == RoomStatus.ACTIVE, Room.id.in_(select(subq.c.room_id)))
    )
    if room_type_id:
        stmt = stmt.where(Room.room_type_id == room_type_id)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("", response_model=list[RoomResponse])
async def list_rooms(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Room).options(selectinload(Room.room_type)))
    return result.scalars().all()
