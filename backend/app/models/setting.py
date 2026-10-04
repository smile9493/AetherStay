from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SystemSetting(Base):
    """单行系统设置项，用于管理自动退房等全局配置。

    系统中只保留一条记录（id=1），通过 upsert 维护。
    """

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    auto_checkout_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_checkout_time: Mapped[str] = mapped_column(String(5), default="12:00", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai", nullable=False)