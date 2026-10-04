from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.setting import SystemSetting
from app.models.user import UserRole
from app.schemas.admin import SystemSettingResponse, SystemSettingUpdate
from app.utils.auth import CurrentUser, RoleChecker

router = APIRouter(prefix="/settings", tags=["admin-settings"])

require_admin = RoleChecker([UserRole.ADMIN])


async def _get_or_create_settings(db: AsyncSession) -> SystemSetting:
    result = await db.execute(select(SystemSetting).where(SystemSetting.id == 1))
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = SystemSetting(id=1)
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
    return setting


@router.get("", response_model=SystemSettingResponse)
async def get_settings(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    return await _get_or_create_settings(db)


@router.put("", response_model=SystemSettingResponse)
async def update_settings(
    data: SystemSettingUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    setting = await _get_or_create_settings(db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(setting, field, value)
    await db.commit()
    await db.refresh(setting)
    return setting