from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.booking import BookingStatus
from app.models.room import RoomStatus
from app.models.user import MembershipTier, UserRole
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
    description: str | None = None
    amenities: str | None = None
    image_url: str | None = None


class RoomTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    base_price: Decimal | None = Field(default=None, gt=0)
    capacity: int | None = Field(default=None, ge=1, le=20)
    total_rooms: int | None = Field(default=None, ge=0)
    description: str | None = None
    amenities: str | None = None
    image_url: str | None = None


class AdminUserResponse(UserResponse):
    is_active: bool
    admin_notes: str | None = None

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    phone: str | None = None
    email: str | None = None
    membership_tier: MembershipTier | None = None
    membership_points: int | None = Field(default=None, ge=0)
    admin_notes: str | None = None


class SystemSettingResponse(BaseModel):
    id: int
    auto_checkout_enabled: bool
    auto_checkout_time: str
    timezone: str

    model_config = {"from_attributes": True}


class SystemSettingUpdate(BaseModel):
    auto_checkout_enabled: bool | None = None
    auto_checkout_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    timezone: str | None = None


class MessageResponse(BaseModel):
    message: str
