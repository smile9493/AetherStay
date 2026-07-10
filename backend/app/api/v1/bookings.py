from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.booking import Booking, BookingStatus
from app.models.room import Room
from app.schemas.admin import PaginatedBookingsResponse
from app.schemas.room import BookingCreate, BookingResponse
from app.services import booking_service
from app.utils.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/bookings", tags=["bookings"])

MyBookingsTab = Literal["all", "pending", "confirmed", "active", "cancelled"]


def _tab_status_filter(tab: MyBookingsTab) -> list:
    if tab == "pending":
        return [Booking.status == BookingStatus.PENDING]
    if tab == "confirmed":
        return [Booking.status == BookingStatus.CONFIRMED]
    if tab == "active":
        return [Booking.status.in_([BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT])]
    if tab == "cancelled":
        return [Booking.status == BookingStatus.CANCELLED]
    return []


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED, operation_id="create_booking")
async def create_booking(
    data: BookingCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new booking with Hold-then-Confirm phase 1 (pessimistic lock)."""
    booking = await booking_service.create_hold_booking(
        db,
        user_id=current_user.user_id,
        room_id=data.room_id,
        check_in=data.check_in,
        check_out=data.check_out,
    )
    return await booking_service.serialize_booking(db, booking)


@router.get("/my", response_model=PaginatedBookingsResponse)
async def my_bookings(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tab: MyBookingsTab = "all",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
):
    conditions = [Booking.user_id == current_user.user_id, *_tab_status_filter(tab)]

    count_stmt = select(func.count()).select_from(Booking).where(and_(*conditions))
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Booking)
        .options(selectinload(Booking.room).selectinload(Room.room_type))
        .where(and_(*conditions))
        .order_by(Booking.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    bookings = result.scalars().all()
    items = await booking_service.serialize_bookings(db, list(bookings))

    return PaginatedBookingsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{booking_id}", response_model=BookingResponse, operation_id="get_booking")
async def get_booking(
    booking_id: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.room).selectinload(Room.room_type))
        .where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.user_id != current_user.user_id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return await booking_service.serialize_booking(db, booking)


@router.post("/{booking_id}/cancel", operation_id="cancel_booking")
async def cancel_booking(
    booking_id: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    is_admin = current_user.role.value == "admin"
    await booking_service.cancel_booking(
        db,
        booking_id=booking_id,
        user_id=current_user.user_id,
        is_admin=is_admin,
    )
    return {"message": "Booking cancelled"}


@router.delete("/{booking_id}", operation_id="delete_booking")
async def delete_booking(
    booking_id: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    is_admin = current_user.role.value == "admin"
    await booking_service.delete_booking(
        db,
        booking_id=booking_id,
        user_id=current_user.user_id,
        is_admin=is_admin,
    )
    return {"message": "Booking deleted"}
