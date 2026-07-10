from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.booking import BookingStatus
from app.models.inventory import InventoryStatus
from app.models.room import RoomStatus


class RoomTypeResponse(BaseModel):
    id: int
    name: str
    base_price: Decimal
    capacity: int
    total_rooms: int

    model_config = {"from_attributes": True}


class RoomResponse(BaseModel):
    id: int
    room_number: str
    room_type_id: int
    status: RoomStatus
    room_type: RoomTypeResponse | None = None

    model_config = {"from_attributes": True}


class RoomSearchParams(BaseModel):
    check_in: date
    check_out: date
    room_type_id: int | None = None


class BookingCreate(BaseModel):
    room_id: int
    check_in: date
    check_out: date


class BookingResponse(BaseModel):
    id: int
    user_id: int
    room_id: int
    check_in: date
    check_out: date
    total_price: Decimal
    status: BookingStatus
    created_at: datetime
    room: RoomResponse | None = None

    model_config = {"from_attributes": True}


class InventoryResponse(BaseModel):
    room_id: int
    date: date
    status: InventoryStatus
    held_until: datetime | None = None
    booking_id: int | None = None

    model_config = {"from_attributes": True}
