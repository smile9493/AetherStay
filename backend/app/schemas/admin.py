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
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedBookingsResponse(BaseModel):
    items: list[BookingResponse]
    total: int
    page: int
    page_size: int


class PaginatedUsersResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int


class PaginatedRoomsResponse(BaseModel):
    items: list[RoomResponse]
    total: int
    page: int
    page_size: int


class PaginatedRoomTypesResponse(BaseModel):
    items: list[RoomTypeResponse]
    total: int
    page: int
    page_size: int


class InventoryRoomItem(BaseModel):
    id: int
    room_number: str
    room_type: str


class PaginatedInventoryResponse(BaseModel):
    rooms: list[InventoryRoomItem]
    dates: list[str]
    matrix: dict[str, dict[str, str]]
    total: int
    page: int
    page_size: int


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


class AutoCheckoutSettingsResponse(BaseModel):
    enabled: bool
    checkout_time: str
    timezone: str = "Asia/Shanghai"


class AutoCheckoutSettingsUpdate(BaseModel):
    enabled: bool
    checkout_time: str = Field(pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    timezone: str = "Asia/Shanghai"
