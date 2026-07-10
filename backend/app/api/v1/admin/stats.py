from datetime import UTC, date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select, case, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.booking import Booking, BookingStatus
from app.models.inventory import DailyRoomInventory, InventoryStatus
from app.models.room import Room, RoomStatus
from app.models.user import User, UserRole
from app.utils.auth import CurrentUser, RoleChecker

router = APIRouter(prefix="/stats", tags=["admin-stats"])

require_admin = RoleChecker([UserRole.ADMIN])


class DashboardStats(BaseModel):
    total_bookings: int
    pending_bookings: int
    confirmed_bookings: int
    active_check_ins: int
    total_revenue: float = 0.0   # sourced from Decimal; cast to float for JSON
    total_rooms: int
    active_rooms: int
    rooms_occupied_today: int
    rooms_available_today: int
    total_users: int
    active_users: int

    model_config = {"from_attributes": True}


@router.get("", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    # Aggregated booking stats in a single query
    booking_stats = await db.execute(
        select(
            func.count(Booking.id).label("total_bookings"),
            func.sum(
                case(
                    (Booking.status == BookingStatus.PENDING, 1),
                    else_=0,
                )
            ).label("pending_bookings"),
            func.sum(
                case(
                    (Booking.status == BookingStatus.CONFIRMED, 1),
                    else_=0,
                )
            ).label("confirmed_bookings"),
            func.sum(
                case(
                    (Booking.status == BookingStatus.CHECKED_IN, 1),
                    else_=0,
                )
            ).label("active_check_ins"),
            func.sum(
                case(
                    (
                        Booking.status.in_([
                            BookingStatus.CONFIRMED,
                            BookingStatus.CHECKED_IN,
                            BookingStatus.CHECKED_OUT,
                        ]),
                        Booking.total_price,
                    ),
                    else_=0,
                )
            ).label("total_revenue"),
        )
    )
    bs = booking_stats.one()

    # Room stats
    room_stats = await db.execute(
        select(
            func.count(Room.id).label("total_rooms"),
            func.sum(
                case(
                    (Room.status == RoomStatus.ACTIVE, 1),
                    else_=0,
                )
            ).label("active_rooms"),
        )
    )
    rs = room_stats.one()

    # User stats
    user_stats = await db.execute(
        select(
            func.count(User.id).label("total_users"),
            func.sum(
                case(
                    (User.is_active.is_(True), 1),
                    else_=0,
                )
            ).label("active_users"),
        )
    )
    us = user_stats.one()

    today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Shanghai")).date()
    now = datetime.now(UTC).replace(tzinfo=None)
    occupied_today = (
        await db.execute(
            select(func.count(func.distinct(DailyRoomInventory.room_id))).where(
                DailyRoomInventory.date == today,
                DailyRoomInventory.status.in_([InventoryStatus.BOOKED, InventoryStatus.HELD]),
            )
        )
    ).scalar_one()

    available_today = (
        await db.execute(
            select(func.count(func.distinct(DailyRoomInventory.room_id)))
            .select_from(DailyRoomInventory)
            .join(Room, DailyRoomInventory.room_id == Room.id)
            .where(
                DailyRoomInventory.date == today,
                Room.status == RoomStatus.ACTIVE,
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
    ).scalar_one()

    return DashboardStats(
        total_bookings=bs.total_bookings or 0,
        pending_bookings=bs.pending_bookings or 0,
        confirmed_bookings=bs.confirmed_bookings or 0,
        active_check_ins=bs.active_check_ins or 0,
        total_revenue=float(bs.total_revenue or 0),
        total_rooms=rs.total_rooms or 0,
        active_rooms=rs.active_rooms or 0,
        rooms_occupied_today=occupied_today or 0,
        rooms_available_today=available_today or 0,
        total_users=us.total_users or 0,
        active_users=us.active_users or 0,
    )
