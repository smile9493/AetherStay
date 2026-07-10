from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.room import RoomType
from app.models.user import UserRole
from app.schemas.admin import RoomTypeCreate, RoomTypeUpdate
from app.schemas.room import RoomTypeResponse
from app.utils.auth import CurrentUser, RoleChecker

router = APIRouter(prefix="/room-types", tags=["admin-room-types"])

require_admin = RoleChecker([UserRole.ADMIN])


@router.get("", response_model=list[RoomTypeResponse])
async def list_room_types(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    result = await db.execute(select(RoomType))
    return result.scalars().all()


@router.post("", response_model=RoomTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_room_type(
    data: RoomTypeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    room_type = RoomType(**data.model_dump())
    db.add(room_type)
    await db.commit()
    await db.refresh(room_type)
    return room_type


@router.put("/{room_type_id}", response_model=RoomTypeResponse)
async def update_room_type(
    room_type_id: int,
    data: RoomTypeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    room_type = await db.get(RoomType, room_type_id)
    if not room_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(room_type, field, value)

    await db.commit()
    await db.refresh(room_type)
    return room_type
