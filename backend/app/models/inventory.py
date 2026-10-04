import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InventoryStatus(str, enum.Enum):
    AVAILABLE = "available"
    HELD = "held"
    BOOKED = "booked"
    MAINTENANCE = "maintenance"


class DailyRoomInventory(Base):
    __tablename__ = "daily_room_inventories"
    __table_args__ = (
        Index("idx_date_status", "date", "status"),
        Index("idx_status_held_until", "status", "held_until"),
    )

    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    status: Mapped[InventoryStatus] = mapped_column(
        Enum(InventoryStatus, values_callable=lambda x: [e.value for e in x]),
        default=InventoryStatus.AVAILABLE,
        nullable=False,
    )
    held_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    booking_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True
    )

    room: Mapped["Room"] = relationship(back_populates="inventories")
