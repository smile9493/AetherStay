from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.booking import Booking, BookingStatus
from app.models.inventory import DailyRoomInventory, InventoryStatus
from app.models.room import Room, RoomStatus
from app.models.user import User, UserRole
from app.utils.auth import CurrentUser, RoleChecker

router = APIRouter(prefix="/stats", tags=["admin-stats"])

require_admin = RoleChecker([UserRole.ADMIN])


@router.get("")
async def get_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    """Dashboard 统计大盘：订单、收入、用户、入住与出租情况。"""
    today = date.today()

    total_bookings = await db.scalar(select(func.count()).select_from(Booking))
    pending_bookings = await db.scalar(
        select(func.count()).select_from(Booking).where(Booking.status == BookingStatus.PENDING)
    )
    today_checkins = await db.scalar(
        select(func.count())
        .select_from(Booking)
        .where(Booking.check_in == today, Booking.status != BookingStatus.CANCELLED)
    )
    total_revenue = await db.scalar(
        select(func.coalesce(func.sum(Booking.total_price), 0)).select_from(Booking).where(
            Booking.status.in_(
                [BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]
            )
        )
    )
    user_count = await db.scalar(select(func.count()).select_from(User))

    total_rooms = await db.scalar(
        select(func.count()).select_from(Room).where(Room.status == RoomStatus.ACTIVE)
    )
    occupied_today = await db.scalar(
        select(func.count())
        .select_from(DailyRoomInventory)
        .where(DailyRoomInventory.date == today, DailyRoomInventory.status == InventoryStatus.BOOKED)
    )

    occupancy_rate = round(occupied_today / total_rooms, 4) if total_rooms else 0.0

    return {
        "total_bookings": total_bookings or 0,
        "pending_bookings": pending_bookings or 0,
        "today_checkins": today_checkins or 0,
        "total_revenue": float(total_revenue or 0),
        "user_count": user_count or 0,
        "total_rooms": total_rooms or 0,
        "occupied_today": occupied_today or 0,
        "occupancy_rate": occupancy_rate,
    }