"""pytest 测试基础设施。

要点：
- 测试使用独立的数据库 ``aetherstay_test``（在 127.0.0.1:3307 上，用 root 创建），
  避免污染开发库 ``aetherstay``。
- 通过环境变量 ``DATABASE_URL`` 在导入应用前覆盖数据库地址（pydantic-settings
  中环境变量优先级高于 .env 文件）。
- 使用 ``httpx.ASGITransport`` 在进程内调用 ASGI 应用，无需启动真实服务；
  但底部是真实的 MySQL，因此悲观锁（``SELECT ... FOR UPDATE NOWAIT``）行为可被真实覆盖。
"""

import os
from datetime import date, timedelta

TEST_DATABASE = "aetherstay_test"
# root 拥有全部库权限，用于创建/初始化测试库；应用运行账号仅授权 aetherstay 库。
ADMIN_DATABASE_URL = "mysql+aiomysql://root:root@127.0.0.1:3307/mysql"
TEST_DATABASE_URL = f"mysql+aiomysql://root:root@127.0.0.1:3307/{TEST_DATABASE}"

# 必须在导入 app 之前设置，否则 engine 会绑定到 .env 中的开发库
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.database import Base, async_session_factory, engine  # noqa: E402
from app.main import app  # noqa: E402

SEED_DAYS = 90


async def _prepare_database() -> None:
    """创建测试库结构并灌入种子数据（幂等：先删后建）。"""
    admin_engine = create_async_engine(ADMIN_DATABASE_URL)
    try:
        async with admin_engine.connect() as conn:
            await conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS {TEST_DATABASE} "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_bin"
                )
            )
            await conn.commit()
    finally:
        await admin_engine.dispose()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    today = date.today()
    async with async_session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO room_types (name, base_price, capacity, total_rooms) VALUES "
                "('标准双床房', 299.00, 2, 10),"
                "('豪华大床房', 499.00, 2, 8),"
                "('行政套房', 899.00, 4, 4)"
            )
        )
        await session.execute(
            text(
                "INSERT INTO rooms (room_number, room_type_id, status) VALUES "
                "('101', 1, 'active'), ('102', 1, 'active'), "
                "('201', 2, 'active'), ('301', 3, 'active')"
            )
        )
        for offset in range(SEED_DAYS):
            inv_date = (today + timedelta(days=offset)).isoformat()
            await session.execute(
                text(
                    "INSERT INTO daily_room_inventories (room_id, date, status) "
                    "SELECT id, :d, 'available' FROM rooms"
                ),
                {"d": inv_date},
            )
        await session.commit()


@pytest.fixture(scope="session", autouse=True)
async def prepare_database():
    await _prepare_database()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(autouse=True)
async def reset_state():
    """每个用例结束后重置预订与房态，保证用例之间隔离。"""
    yield
    async with async_session_factory() as session:
        # 先清空房态对订单的外键引用，再删除订单，避免外键约束冲突
        await session.execute(
            text(
                "UPDATE daily_room_inventories "
                "SET status='available', booking_id=NULL, held_until=NULL"
            )
        )
        await session.execute(text("DELETE FROM bookings"))
        await session.execute(text("DELETE FROM refresh_token_sessions"))
        await session.execute(text("DELETE FROM system_settings"))
        await session.commit()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register_user(client: AsyncClient, username: str, password: str = "secret123"):
    return await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )


async def login_user(client: AsyncClient, username: str, password: str = "secret123"):
    return await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )


async def register_and_login(client: AsyncClient, username: str, password: str = "secret123"):
    """注册并登录，登录成功后 client 的 cookie jar 自动携带 access_token。"""
    await register_user(client, username, password)
    resp = await login_user(client, username, password)
    return resp