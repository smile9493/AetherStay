import enum
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RoomStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class RoomType(Base):
    __tablename__ = "room_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    capacity: Mapped[int] = mapped_column(SmallInteger, default=2, nullable=False)
    total_rooms: Mapped[int] = mapped_column(default=0, nullable=False)

    rooms: Mapped[list["Room"]] = relationship(back_populates="room_type")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_number: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id"), nullable=False, index=True)
    status: Mapped[RoomStatus] = mapped_column(
        Enum(RoomStatus, values_callable=lambda x: [e.value for e in x]),
        default=RoomStatus.ACTIVE,
        nullable=False,
    )

    room_type: Mapped["RoomType"] = relationship(back_populates="rooms")
    inventories: Mapped[list["DailyRoomInventory"]] = relationship(back_populates="room")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="room")
