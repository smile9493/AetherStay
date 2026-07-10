from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.booking import Booking, BookingStatus
from app.models.room import Room
from app.models.user import UserRole
from app.schemas.admin import (
    AdminBookingCreate,
    AdminBookingRoomChange,
    AdminBookingUpdate,
    PaginatedBookingsResponse,
)
from app.schemas.room import BookingResponse
from app.services import booking_service
from app.utils.auth import CurrentUser, RoleChecker

router = APIRouter(prefix="/bookings", tags=["admin-bookings"])

require_admin = RoleChecker([UserRole.ADMIN])


def _booking_filters(
    status: BookingStatus | None,
    check_in_from: date | None,
    check_in_to: date | None,
) -> list:
    conditions = []
    if status:
        conditions.append(Booking.status == status)
    if check_in_from:
        conditions.append(Booking.check_in >= check_in_from)
    if check_in_to:
        conditions.append(Booking.check_in <= check_in_to)
    return conditions


@router.get("", response_model=PaginatedBookingsResponse)
async def list_bookings(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
    status: BookingStatus | None = None,
    check_in_from: date | None = None,
    check_in_to: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    conditions = _booking_filters(status, check_in_from, check_in_to)

    count_stmt = select(func.count()).select_from(Booking)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Booking)
        .options(selectinload(Booking.room).selectinload(Room.room_type))
        .order_by(Booking.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if conditions:
        stmt = stmt.where(and_(*conditions))

    result = await db.execute(stmt)
    bookings = result.scalars().all()
    items = await booking_service.serialize_bookings(db, list(bookings))

    return PaginatedBookingsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking_for_user(
    data: AdminBookingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    booking = await booking_service.create_admin_booking(
        db,
        user_id=data.user_id,
        room_id=data.room_id,
        check_in=data.check_in,
        check_out=data.check_out,
        notes=data.notes,
        auto_confirm=data.auto_confirm,
    )
    return await booking_service.serialize_booking(db, booking)


@router.put("/{booking_id}", response_model=BookingResponse)
async def update_booking(
    booking_id: int,
    data: AdminBookingUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    if data.check_in is None and data.check_out is None and data.notes is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    booking = await booking_service.update_booking_details(
        db,
        booking_id,
        check_in=data.check_in,
        check_out=data.check_out,
        notes=data.notes,
    )
    return await booking_service.serialize_booking(db, booking)


@router.put("/{booking_id}/room", response_model=BookingResponse)
async def change_booking_room(
    booking_id: int,
    data: AdminBookingRoomChange,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    booking = await booking_service.change_booking_room(db, booking_id, data.room_id)
    return await booking_service.serialize_booking(db, booking)


@router.post("/{booking_id}/confirm", response_model=BookingResponse)
async def confirm_booking(
    booking_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    booking = await booking_service.confirm_booking(db, booking_id)
    return await booking_service.serialize_booking(db, booking)


@router.post("/{booking_id}/check-in", response_model=BookingResponse)
async def check_in(
    booking_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    booking = await booking_service.check_in_booking(db, booking_id)
    return await booking_service.serialize_booking(db, booking)


@router.post("/{booking_id}/check-out", response_model=BookingResponse)
async def check_out(
    booking_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    booking = await booking_service.check_out_booking(db, booking_id)
    return await booking_service.serialize_booking(db, booking)
