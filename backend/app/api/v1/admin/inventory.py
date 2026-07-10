"""Admin inventory calendar API — room × date matrix for occupancy visualization."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.inventory import DailyRoomInventory, InventoryStatus
from app.models.room import Room, RoomStatus
from app.models.user import UserRole
from app.utils.auth import CurrentUser, RoleChecker

router = APIRouter(prefix="/inventory", tags=["admin-inventory"])
admin_only = RoleChecker([UserRole.ADMIN])


@router.get("")
async def get_inventory_matrix(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(admin_only)],
    start_date: Annotated[
        date, Query(description="Start date (YYYY-MM-DD)")
    ] = date.today(),
    end_date: Annotated[
        date | None, Query(description="End date (YYYY-MM-DD), defaults to start + 14 days")
    ] = None,
):
    """返回房间 × 日期房态矩阵，单元格值为 available / held / booked / maintenance。"""
    if end_date is None:
        end_date = start_date + timedelta(days=14)
    if end_date <= start_date:
        end_date = start_date + timedelta(days=14)

    # 1. 获取所有 active 房间
    rooms_result = await db.execute(
        select(Room)
        .options(selectinload(Room.room_type))
        .where(Room.status == RoomStatus.ACTIVE)
        .order_by(Room.room_number)
    )
    rooms = rooms_result.scalars().all()

    # 2. 构建日期列表
    dates: list[str] = []
    cursor = start_date
    while cursor <= end_date:
        dates.append(cursor.isoformat())
        cursor += timedelta(days=1)

    # 3. 批量查询库存
    inventories_result = await db.execute(
        select(DailyRoomInventory)
        .where(
            DailyRoomInventory.room_id.in_([r.id for r in rooms]),
            DailyRoomInventory.date >= start_date,
            DailyRoomInventory.date <= end_date,
        )
    )
    inv_rows = inventories_result.scalars().all()

    # 4. 组装矩阵
    matrix: dict[str, dict[str, str]] = {}
    for r in rooms:
        matrix[str(r.id)] = {}

    default_status = InventoryStatus.AVAILABLE.value
    date_set = set(dates)
    for inv in inv_rows:
        d = inv.date.isoformat()
        if d in date_set:
            matrix[str(inv.room_id)][d] = inv.status.value

    # 剩余日期填充 available
    for r in rooms:
        for d in dates:
            matrix[str(r.id)].setdefault(d, default_status)

    return {
        "rooms": [
            {
                "id": r.id,
                "room_number": r.room_number,
                "room_type": r.room_type.name if r.room_type else "",
            }
            for r in rooms
        ],
        "dates": dates,
        "matrix": matrix,
    }
