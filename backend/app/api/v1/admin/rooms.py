from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.room import Room, RoomType
from app.models.user import UserRole
from app.schemas.admin import RoomCreate, RoomUpdate
from app.schemas.room import RoomResponse
from app.services import inventory_service
from app.services.transaction import transaction
from app.utils.auth import CurrentUser, RoleChecker

router = APIRouter(prefix="/rooms", tags=["admin-rooms"])

require_admin = RoleChecker([UserRole.ADMIN])


@router.get("", response_model=list[RoomResponse])
async def list_rooms(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    result = await db.execute(select(Room).options(selectinload(Room.room_type)))
    return result.scalars().all()


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    data: RoomCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    room_type = await db.get(RoomType, data.room_type_id)
    if not room_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")

    existing = await db.execute(select(Room).where(Room.room_number == data.room_number))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room number already exists")

    async with transaction(db):
        room = Room(
            room_number=data.room_number,
            room_type_id=data.room_type_id,
            status=data.status,
        )
        db.add(room)
        await db.flush()
        await inventory_service.generate_inventory_for_room(db, room.id)
        room_type.total_rooms += 1
        room_id = room.id

    result = await db.execute(
        select(Room).options(selectinload(Room.room_type)).where(Room.id == room_id)
    )
    return result.scalar_one()


@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: int,
    data: RoomUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    if data.room_number is not None:
        room.room_number = data.room_number
    if data.room_type_id is not None:
        room_type = await db.get(RoomType, data.room_type_id)
        if not room_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
        room.room_type_id = data.room_type_id
    if data.status is not None:
        room.status = data.status

    await db.commit()
    await db.refresh(room, ["room_type"])
    result = await db.execute(
        select(Room).options(selectinload(Room.room_type)).where(Room.id == room_id)
    )
    return result.scalar_one()
