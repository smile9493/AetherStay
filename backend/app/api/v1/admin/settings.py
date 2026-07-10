from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import UserRole
from app.schemas.admin import AutoCheckoutSettingsResponse, AutoCheckoutSettingsUpdate
from app.services import settings_service
from app.utils.auth import CurrentUser, RoleChecker

router = APIRouter(prefix="/settings", tags=["admin-settings"])
admin_only = RoleChecker([UserRole.ADMIN])


@router.get("/auto-checkout", response_model=AutoCheckoutSettingsResponse)
async def get_auto_checkout_settings(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(admin_only)],
):
    settings = await settings_service.get_auto_checkout_settings(db)
    return AutoCheckoutSettingsResponse(
        enabled=settings.enabled,
        checkout_time=settings.checkout_time,
        timezone=settings.timezone,
    )


@router.put("/auto-checkout", response_model=AutoCheckoutSettingsResponse)
async def update_auto_checkout_settings(
    data: AutoCheckoutSettingsUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(admin_only)],
):
    settings = await settings_service.update_auto_checkout_settings(
        db,
        enabled=data.enabled,
        checkout_time=data.checkout_time,
        timezone=data.timezone,
    )
    return AutoCheckoutSettingsResponse(
        enabled=settings.enabled,
        checkout_time=settings.checkout_time,
        timezone=settings.timezone,
    )
