from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.admin import AdminUserResponse, MessageResponse, PaginatedUsersResponse
from app.utils.auth import CurrentUser, RoleChecker

router = APIRouter(prefix="/users", tags=["admin-users"])

require_admin = RoleChecker([UserRole.ADMIN])


@router.get("", response_model=PaginatedUsersResponse)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    total = (await db.execute(select(func.count()).select_from(User))).scalar_one()

    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    return PaginatedUsersResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
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

    user.is_active = False
    await db.commit()
    return MessageResponse(message="User disabled")
