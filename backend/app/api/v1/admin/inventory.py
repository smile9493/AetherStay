"""Admin inventory calendar API — room × date matrix for occupancy visualization."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.inventory import DailyRoomInventory, InventoryStatus
from app.models.room import Room, RoomStatus
from app.models.user import UserRole
from app.schemas.admin import InventoryRoomItem, PaginatedInventoryResponse
from app.utils.auth import CurrentUser, RoleChecker

router = APIRouter(prefix="/inventory", tags=["admin-inventory"])
admin_only = RoleChecker([UserRole.ADMIN])


@router.get("", response_model=PaginatedInventoryResponse)
async def get_inventory_matrix(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(admin_only)],
    start_date: Annotated[
        date | None, Query(description="Start date (YYYY-MM-DD), defaults to today")
    ] = None,
    end_date: Annotated[
        date | None, Query(description="End date (YYYY-MM-DD), defaults to start + 14 days")
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
):
    """返回房间 × 日期房态矩阵（按房间分页）。"""
    if start_date is None:
        start_date = date.today()
    if end_date is None:
        end_date = start_date + timedelta(days=14)
    if end_date <= start_date:
        end_date = start_date + timedelta(days=14)

    total = (
        await db.execute(
            select(func.count()).select_from(Room).where(Room.status == RoomStatus.ACTIVE)
        )
    ).scalar_one()

    rooms_result = await db.execute(
        select(Room)
        .options(selectinload(Room.room_type))
        .where(Room.status == RoomStatus.ACTIVE)
        .order_by(Room.room_number)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rooms = rooms_result.scalars().all()

    dates: list[str] = []
    cursor = start_date
    while cursor <= end_date:
        dates.append(cursor.isoformat())
        cursor += timedelta(days=1)

    room_ids = [r.id for r in rooms]
    matrix: dict[str, dict[str, str]] = {str(r.id): {} for r in rooms}

    if room_ids:
        inventories_result = await db.execute(
            select(DailyRoomInventory).where(
                DailyRoomInventory.room_id.in_(room_ids),
                DailyRoomInventory.date >= start_date,
                DailyRoomInventory.date <= end_date,
            )
        )
        inv_rows = inventories_result.scalars().all()

        default_status = InventoryStatus.AVAILABLE.value
        date_set = set(dates)
        for inv in inv_rows:
            d = inv.date.isoformat()
            if d in date_set:
                matrix[str(inv.room_id)][d] = inv.status.value

        for r in rooms:
            for d in dates:
                matrix[str(r.id)].setdefault(d, default_status)

    return PaginatedInventoryResponse(
        rooms=[
            InventoryRoomItem(
                id=r.id,
                room_number=r.room_number,
                room_type=r.room_type.name if r.room_type else "",
            )
            for r in rooms
        ],
        dates=dates,
        matrix=matrix,
        total=total,
        page=page,
        page_size=page_size,
    )
