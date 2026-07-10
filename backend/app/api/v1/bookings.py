from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.booking import Booking
from app.models.room import Room
from app.schemas.room import BookingCreate, BookingResponse
from app.services import booking_service
from app.utils.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED, operation_id="create_booking")
async def create_booking(
    data: BookingCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new booking with Hold-then-Confirm phase 1 (pessimistic lock)."""
    return await booking_service.create_hold_booking(
        db,
        user_id=current_user.user_id,
        room_id=data.room_id,
        check_in=data.check_in,
        check_out=data.check_out,
    )


@router.get("/my", response_model=list[BookingResponse])
async def my_bookings(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.room).selectinload(Room.room_type))
        .where(Booking.user_id == current_user.user_id)
        .order_by(Booking.created_at.desc())
    )
    return result.scalars().all()


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
    return booking


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
