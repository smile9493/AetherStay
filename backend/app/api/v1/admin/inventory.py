from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.inventory import DailyRoomInventory, InventoryStatus
from app.models.room import Room, RoomStatus
from app.models.user import UserRole
from app.utils.auth import CurrentUser, RoleChecker

router = APIRouter(prefix="/inventory", tags=["admin-inventory"])

require_admin = RoleChecker([UserRole.ADMIN])


@router.get("")
async def get_inventory_matrix(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
    start: date | None = Query(default=None, description="起始日期，缺省为今天"),
    end: date | None = Query(default=None, description="结束日期，缺省为起始日期+14天"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
):
    """房态日历矩阵：房间 × 日期 二维房态，按房间分页，默认 14 天窗口。"""
    if start is None:
        start = date.today()
    if end is None:
        end = start + timedelta(days=14)

    # 分页查询 ACTIVE 房间
    total_stmt = select(Room).where(Room.status == RoomStatus.ACTIVE).order_by(Room.id)
    total = len((await db.execute(total_stmt)).scalars().all())

    rooms_stmt = (
        select(Room)
        .options(selectinload(Room.room_type))
        .where(Room.status == RoomStatus.ACTIVE)
        .order_by(Room.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rooms = (await db.execute(rooms_stmt)).scalars().all()
    if not rooms:
        return {"items": [], "total": total, "page": page, "page_size": page_size}

    room_ids = [r.id for r in rooms]
    records = (
        await db.execute(
            select(DailyRoomInventory).where(
                and_(
                    DailyRoomInventory.room_id.in_(room_ids),
                    DailyRoomInventory.date >= start,
                    DailyRoomInventory.date < end,
                )
            )
        )
    ).scalars().all()

    # 每个房间默认 AVAILABLE，再覆盖实际房态
    matrix: dict[int, dict[str, str]] = {
        r.id: {
            (start + timedelta(days=offset)).isoformat(): InventoryStatus.AVAILABLE.value
            for offset in range((end - start).days)
        }
        for r in rooms
    }
    for rec in records:
        matrix.setdefault(rec.room_id, {})[rec.date.isoformat()] = rec.status.value

    items = [
        {
            "room_id": r.id,
            "room_number": r.room_number,
            "room_type": r.room_type.name if r.room_type else None,
            "dates": matrix[r.id],
        }
        for r in rooms
    ]

    return {"items": items, "total": total, "page": page, "page_size": page_size}