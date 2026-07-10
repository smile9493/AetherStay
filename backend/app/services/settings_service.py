import re
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_setting import SystemSetting

CHECKOUT_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

AUTO_CHECKOUT_KEYS = ("auto_checkout_enabled", "auto_checkout_time", "timezone")

DEFAULTS = {
    "auto_checkout_enabled": "true",
    "auto_checkout_time": "12:00",
    "timezone": "Asia/Shanghai",
}


@dataclass
class AutoCheckoutSettings:
    enabled: bool
    checkout_time: str
    timezone: str


_cache: AutoCheckoutSettings | None = None
_cache_version: datetime | None = None


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def validate_checkout_time(value: str) -> str:
    if not CHECKOUT_TIME_RE.match(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="checkout_time must be HH:MM (00:00–23:59)",
        )
    return value


async def _get_settings_map(db: AsyncSession, keys: tuple[str, ...]) -> dict[str, str]:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key.in_(keys)))
    rows = {row.key: row.value for row in result.scalars().all()}
    return {key: rows.get(key, DEFAULTS[key]) for key in keys}


async def _cache_version_for_keys(db: AsyncSession, keys: tuple[str, ...]) -> datetime | None:
    result = await db.execute(
        select(func.max(SystemSetting.updated_at)).where(SystemSetting.key.in_(keys))
    )
    return result.scalar_one_or_none()


def invalidate_auto_checkout_cache() -> None:
    global _cache, _cache_version
    _cache = None
    _cache_version = None


async def get_auto_checkout_settings(db: AsyncSession) -> AutoCheckoutSettings:
    global _cache, _cache_version

    version = await _cache_version_for_keys(db, AUTO_CHECKOUT_KEYS)
    if _cache is not None and _cache_version == version:
        return _cache

    values = await _get_settings_map(db, AUTO_CHECKOUT_KEYS)
    settings = AutoCheckoutSettings(
        enabled=_parse_bool(values["auto_checkout_enabled"]),
        checkout_time=values["auto_checkout_time"],
        timezone=values["timezone"],
    )
    _cache = settings
    _cache_version = version
    return settings


async def update_auto_checkout_settings(
    db: AsyncSession,
    *,
    enabled: bool,
    checkout_time: str,
    timezone: str = "Asia/Shanghai",
) -> AutoCheckoutSettings:
    checkout_time = validate_checkout_time(checkout_time)

    updates = {
        "auto_checkout_enabled": "true" if enabled else "false",
        "auto_checkout_time": checkout_time,
        "timezone": timezone,
    }

    for key, value in updates.items():
        result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        row = result.scalar_one_or_none()
        if row:
            row.value = value
        else:
            db.add(SystemSetting(key=key, value=value))

    await db.commit()
    invalidate_auto_checkout_cache()
    return await get_auto_checkout_settings(db)


async def seed_default_settings(db: AsyncSession) -> None:
    """Insert default settings if missing (for tests and fresh DB)."""
    for key, value in DEFAULTS.items():
        result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        if result.scalar_one_or_none() is None:
            db.add(SystemSetting(key=key, value=value))
    await db.commit()
