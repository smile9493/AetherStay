from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.booking import Booking, BookingStatus
from app.models.room import Room
from app.models.user import UserRole
from app.schemas.room import BookingResponse
from app.services import booking_service
from app.utils.auth import CurrentUser, RoleChecker

router = APIRouter(prefix="/bookings", tags=["admin-bookings"])

require_admin = RoleChecker([UserRole.ADMIN])


@router.get("", response_model=list[BookingResponse])
async def list_bookings(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
    status: BookingStatus | None = None,
    check_in_from: date | None = None,
    check_in_to: date | None = None,
):
    stmt = select(Booking).options(selectinload(Booking.room).selectinload(Room.room_type))
    conditions = []
    if status:
        conditions.append(Booking.status == status)
    if check_in_from:
        conditions.append(Booking.check_in >= check_in_from)
    if check_in_to:
        conditions.append(Booking.check_in <= check_in_to)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(Booking.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{booking_id}/confirm", response_model=BookingResponse)
async def confirm_booking(
    booking_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    return await booking_service.confirm_booking(db, booking_id)


@router.post("/{booking_id}/check-in", response_model=BookingResponse)
async def check_in(
    booking_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    return await booking_service.check_in_booking(db, booking_id)


@router.post("/{booking_id}/check-out", response_model=BookingResponse)
async def check_out(
    booking_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    return await booking_service.check_out_booking(db, booking_id)
