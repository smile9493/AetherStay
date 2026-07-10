from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.booking import Booking, BookingStatus
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminUserDetailResponse,
    AdminUserResponse,
    AdminUserUpdate,
    MessageResponse,
    PaginatedUsersResponse,
    UserBookingStats,
)
from app.utils.auth import CurrentUser, RoleChecker

router = APIRouter(prefix="/users", tags=["admin-users"])

require_admin = RoleChecker([UserRole.ADMIN])

_PAID_STATUSES = (
    BookingStatus.CONFIRMED,
    BookingStatus.CHECKED_IN,
    BookingStatus.CHECKED_OUT,
)


async def _user_booking_stats(db: AsyncSession, user_id: int) -> UserBookingStats:
    result = await db.execute(
        select(
            func.count(Booking.id).label("total"),
            func.sum(
                case(
                    (Booking.status == BookingStatus.CHECKED_OUT, 1),
                    else_=0,
                )
            ).label("completed"),
            func.sum(
                case(
                    (Booking.status.in_(_PAID_STATUSES), Booking.total_price),
                    else_=0,
                )
            ).label("spent"),
            func.max(Booking.created_at).label("last_at"),
        ).where(
            Booking.user_id == user_id,
            Booking.status != BookingStatus.CANCELLED,
        )
    )
    row = result.one()
    return UserBookingStats(
        total_bookings=row.total or 0,
        completed_bookings=row.completed or 0,
        total_spent=float(row.spent or 0),
        last_booking_at=row.last_at,
    )


@router.get("", response_model=PaginatedUsersResponse)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    membership_tier: str | None = None,
):
    count_stmt = select(func.count()).select_from(User)
    stmt = select(User).order_by(User.created_at.desc())

    if membership_tier:
        from app.models.user import MembershipTier

        try:
            tier = MembershipTier(membership_tier)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid membership tier",
            )
        count_stmt = count_stmt.where(User.membership_tier == tier)
        stmt = stmt.where(User.membership_tier == tier)

    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    items = result.scalars().all()

    return PaginatedUsersResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=AdminUserDetailResponse)
async def get_user_detail(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stats = await _user_booking_stats(db, user_id)
    return AdminUserDetailResponse(
        **AdminUserResponse.model_validate(user).model_dump(),
        admin_notes=user.admin_notes,
        stats=stats,
    )


@router.put("/{user_id}", response_model=AdminUserDetailResponse)
async def update_user(
    user_id: int,
    data: AdminUserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_admin)],
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user_id == current_user.user_id and data.is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable yourself")

    if user.role == UserRole.ADMIN and data.is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable admin accounts")

    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    for field, value in updates.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    stats = await _user_booking_stats(db, user_id)
    return AdminUserDetailResponse(
        **AdminUserResponse.model_validate(user).model_dump(),
        admin_notes=user.admin_notes,
        stats=stats,
    )


@router.post("/{user_id}/disable", response_model=MessageResponse)
async def disable_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_admin)],
):
    if user_id == current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable yourself")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable admin accounts")

    user.is_active = False
    await db.commit()
    return MessageResponse(message="User disabled")
