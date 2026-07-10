from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.booking import BookingStatus
from app.models.room import RoomStatus
from app.models.user import UserRole
from app.schemas.auth import UserResponse
from app.schemas.room import BookingResponse, RoomResponse, RoomTypeResponse


class AdminBookingListParams(BaseModel):
    status: BookingStatus | None = None
    check_in_from: date | None = None
    check_in_to: date | None = None


class RoomCreate(BaseModel):
    room_number: str = Field(min_length=1, max_length=16)
    room_type_id: int
    status: RoomStatus = RoomStatus.ACTIVE


class RoomUpdate(BaseModel):
    room_number: str | None = Field(default=None, min_length=1, max_length=16)
    room_type_id: int | None = None
    status: RoomStatus | None = None


class RoomTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    base_price: Decimal = Field(gt=0)
    capacity: int = Field(ge=1, le=20)
    total_rooms: int = Field(ge=0)
    description: str | None = Field(default=None, max_length=512)
    amenities: str | None = Field(default=None, max_length=512)
    image_url: str | None = Field(default=None, max_length=256)


class RoomTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    base_price: Decimal | None = Field(default=None, gt=0)
    capacity: int | None = Field(default=None, ge=1, le=20)
    total_rooms: int | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=512)
    amenities: str | None = Field(default=None, max_length=512)
    image_url: str | None = Field(default=None, max_length=256)


class AdminUserResponse(UserResponse):
    is_active: bool

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
