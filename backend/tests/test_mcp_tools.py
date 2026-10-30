"""意见6·e6b：故障恢复与 MCP 异常调用测试。

覆盖：限流器、未知工具、敏感操作人工确认、审计日志、工具级 RBAC，
以及预订失败的事务回滚一致性（故障恢复）。
"""

import json

from sqlalchemy import func, select

from app.agent.tools import CUSTOMER_TOOLS, ADMIN_TOOLS, execute_tool, get_tools
from app.database import async_session_factory
from app.models.audit import ToolCallAuditLog
from app.models.booking import Booking
from app.models.inventory import DailyRoomInventory, InventoryStatus
from app.models.user import User, UserRole
from app.utils.auth import CurrentUser, hash_password
from app.utils.rate_limit import SlidingWindowRateLimiter
from tests.conftest import register_and_login


async def _mk_user(username: str, role: UserRole = UserRole.CUSTOMER, active: bool = True) -> User:
    async with async_session_factory() as session:
        user = User(username=username, password_hash=hash_password("secret123"), role=role, is_active=active)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _admin(username: str) -> CurrentUser:
    u = await _mk_user(username, UserRole.ADMIN)
    return CurrentUser(user_id=u.id, username=u.username, role=u.role)


# ---------- 限流器（单元） ----------

def test_rate_limiter_blocks_after_threshold():
    rl = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    assert all(rl.allow("k") for _ in range(3))
    assert rl.allow("k") is False


# ---------- 未知工具 / 敏感确认 / 审计 / RBAC ----------

async def test_execute_tool_unknown_tool_returns_error():
    async with async_session_factory() as session:
        out = await execute_tool(session, None, "no_such_tool", {})
        assert json.loads(out)["error"].startswith("未知工具")


async def test_execute_tool_sensitive_requires_confirm():
    admin = await _admin("mcp_admin_1")
    async with async_session_factory() as session:
        out = await execute_tool(session, admin, "admin_disable_user", {"user_id": 999999})
        assert "confirm=true" in json.loads(out)["error"]


async def test_execute_tool_admin_disable_user_writes_audit():
    admin = await _admin("mcp_admin_2")
    target = await _mk_user("mcp_victim_2")
    async with async_session_factory() as session:
        out = await execute_tool(
            session, admin, "admin_disable_user", {"user_id": target.id, "confirm": True}
        )
        body = json.loads(out)
        assert "已被禁用" in body.get("message", "")

    # 用户确被禁用，且留下审计日志
    async with async_session_factory() as session:
        t = await session.get(User, target.id)
        assert t.is_active is False
        rows = (await session.execute(
            select(ToolCallAuditLog).where(ToolCallAuditLog.tool_name == "admin_disable_user")
        )).scalars().all()
        assert any(r.user_id == admin.user_id and r.success for r in rows)


async def test_execute_tool_customer_cannot_call_admin_tool():
    """越权：顾客即使带 confirm=true 调用管理员工具也应被拒，目标不被禁用，且留失败审计。"""
    customer = await _mk_user("mcp_customer_1", UserRole.CUSTOMER)
    target = await _mk_user("mcp_victim_3")
    cu = CurrentUser(user_id=customer.id, username=customer.username, role=customer.role)
    async with async_session_factory() as session:
        out = await execute_tool(
            session, cu, "admin_disable_user", {"user_id": target.id, "confirm": True}
        )
        assert "需要管理员权限" in json.loads(out)["error"]

    async with async_session_factory() as session:
        t = await session.get(User, target.id)
        assert t.is_active is True
        rows = (await session.execute(
            select(ToolCallAuditLog).where(
                ToolCallAuditLog.tool_name == "admin_disable_user",
                ToolCallAuditLog.user_id == customer.id,
            )
        )).scalars().all()
        assert any(not r.success for r in rows)


async def test_execute_tool_sensitive_confirm_failure_is_audited():
    """确认失效：敏感操作未带 confirm 时被拒绝，且审计记为失败。"""
    admin = await _admin("mcp_admin_3")
    async with async_session_factory() as session:
        out = await execute_tool(session, admin, "admin_disable_user", {"user_id": 999999})
        assert "confirm=true" in json.loads(out)["error"]

    async with async_session_factory() as session:
        rows = (await session.execute(
            select(ToolCallAuditLog).where(
                ToolCallAuditLog.tool_name == "admin_disable_user",
                ToolCallAuditLog.user_id == admin.user_id,
            )
        )).scalars().all()
        assert any(not r.success for r in rows)


async def test_get_tools_rbac_filters_admin():
    customer = CurrentUser(user_id=1, username="c", role=UserRole.CUSTOMER)
    admin = CurrentUser(user_id=2, username="a", role=UserRole.ADMIN)
    cnames = {t["function"]["name"] for t in get_tools(customer)}
    anames = {t["function"]["name"] for t in get_tools(admin)}
    assert cnames == {t["function"]["name"] for t in CUSTOMER_TOOLS}
    assert "admin_disable_user" in anames and "admin_disable_user" not in cnames
    assert len(anames) == len(CUSTOMER_TOOLS) + len(ADMIN_TOOLS)


# ---------- 故障恢复：预订失败回滚，不残留中间态 ----------

async def test_booking_failure_rolls_back_no_partial_state(client):
    await register_and_login(client, "booker_fault")
    async with async_session_factory() as session:
        before_bookings = (await session.execute(select(func.count()).select_from(Booking))).scalar()

    # 预订不存在的房间 → 404，事务应回滚，不留任何 HELD 房态或脏订单
    resp = await client.post(
        "/api/v1/bookings",
        json={"room_id": 999999, "check_in": "2027-01-01", "check_out": "2027-01-03"},
    )
    assert resp.status_code == 404

    async with async_session_factory() as session:
        held = (await session.execute(
            select(func.count()).select_from(DailyRoomInventory).where(
                DailyRoomInventory.status == InventoryStatus.HELD
            )
        )).scalar()
        after_bookings = (await session.execute(select(func.count()).select_from(Booking))).scalar()
        assert held == 0
        assert after_bookings == before_bookings