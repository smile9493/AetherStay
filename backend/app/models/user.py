import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"


class MembershipTier(str, enum.Enum):
    STANDARD = "standard"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.CUSTOMER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    membership_tier: Mapped[MembershipTier] = mapped_column(
        Enum(MembershipTier, values_callable=lambda x: [e.value for e in x]),
        default=MembershipTier.STANDARD,
        nullable=False,
    )
    membership_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    admin_notes: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")
