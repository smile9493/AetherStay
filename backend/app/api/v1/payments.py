from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.booking import Booking
from app.schemas.room import BookingResponse
from app.services import booking_service
from app.utils.auth import CurrentUser, get_current_user

router = APIRouter(tags=["payments"])


@router.post(
    "/bookings/{booking_id}/pay",
    response_model=BookingResponse,
    operation_id="confirm_booking_payment",
)
async def pay_booking(
    booking_id: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Simulate payment callback to confirm a pending booking (Hold phase 2)."""
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return await booking_service.serialize_booking(db, await booking_service.confirm_booking(db, booking_id))
