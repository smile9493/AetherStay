from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.booking import Booking, BookingStatus
from app.schemas.room import BookingCreate, BookingResponse
from app.utils.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED, operation_id="create_booking")
async def create_booking(
    data: BookingCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new booking (Hold phase). Full pessimistic lock logic to be implemented in Phase 2."""
    if data.check_out <= data.check_in:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date range")

    from app.models.room import Room

    room_result = await db.execute(
        select(Room).options(selectinload(Room.room_type)).where(Room.id == data.room_id)
    )
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    nights = (data.check_out - data.check_in).days
    total_price = room.room_type.base_price * nights

    booking = Booking(
        user_id=current_user.user_id,
        room_id=data.room_id,
        check_in=data.check_in,
        check_out=data.check_out,
        total_price=total_price,
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    result = await db.execute(
        select(Booking).options(selectinload(Booking.room).selectinload(Room.room_type)).where(Booking.id == booking.id)
    )
    return result.scalar_one()


@router.get("/my", response_model=list[BookingResponse])
async def my_bookings(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.models.room import Room

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
    from app.models.room import Room

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
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if booking.status in (BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel this booking")

    booking.status = BookingStatus.CANCELLED
    await db.commit()
    return {"message": "Booking cancelled"}
