"""预订链路测试：创建（Hold）、取消、支付确认、我的订单，以及防超卖并发。"""

import asyncio
from datetime import date, timedelta

from sqlalchemy import func, select

from app.database import async_session_factory
from app.models.booking import Booking
from app.models.inventory import DailyRoomInventory, InventoryStatus
from tests.conftest import register_and_login

NIGHTS = 3


def _range(today: date, start: int = 10):
    check_in = (today + timedelta(days=start)).isoformat()
    check_out = (today + timedelta(days=start + NIGHTS)).isoformat()
    return check_in, check_out


async def _pick_available_room(client, today: date):
    """搜索并返回首个可用房间（含房型），以及起止日期。"""
    check_in, check_out = _range(today)
    resp = await client.get(
        "/api/v1/rooms/search",
        params={"check_in": check_in, "check_out": check_out},
    )
    assert resp.status_code == 200
    rooms = resp.json()
    assert rooms, "种子数据应保证存在可用房间"
    return rooms[0], check_in, check_out


async def _book(client, room_id, check_in, check_out):
    return await client.post(
        "/api/v1/bookings",
        json={"room_id": room_id, "check_in": check_in, "check_out": check_out},
    )


async def test_create_booking_holds_room_and_hides_from_search(client):
    await register_and_login(client, "booker_hide")
    today = date.today()
    room, check_in, check_out = await _pick_available_room(client, today)
    room_id = room["id"]
    nightly_price = float(room["room_type"]["base_price"])

    resp = await _book(client, room_id, check_in, check_out)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["room_id"] == room_id
    assert float(body["total_price"]) == nightly_price * NIGHTS

    # Hold 后该房不再出现在可用列表
    remain = (
        await client.get(
            "/api/v1/rooms/search",
            params={"check_in": check_in, "check_out": check_out},
        )
    ).json()
    assert all(r["id"] != room_id for r in remain)


async def test_cancel_booking_releases_room(client):
    await register_and_login(client, "booker_cancel")
    today = date.today()
    room, check_in, check_out = await _pick_available_room(client, today)
    room_id = room["id"]

    create = await _book(client, room_id, check_in, check_out)
    assert create.status_code == 201
    booking_id = create.json()["id"]

    cancel = await client.post(f"/api/v1/bookings/{booking_id}/cancel")
    assert cancel.status_code == 200

    remain = (
        await client.get(
            "/api/v1/rooms/search",
            params={"check_in": check_in, "check_out": check_out},
        )
    ).json()
    assert any(r["id"] == room_id for r in remain)


async def test_payment_confirms_booking(client):
    await register_and_login(client, "booker_pay")
    today = date.today()
    room, check_in, check_out = await _pick_available_room(client, today)

    create = await _book(client, room["id"], check_in, check_out)
    assert create.status_code == 201
    booking_id = create.json()["id"]

    pay = await client.post(f"/api/v1/bookings/{booking_id}/pay")
    assert pay.status_code == 200
    assert pay.json()["status"] == "confirmed"


async def test_my_bookings_returns_own(client):
    await register_and_login(client, "booker_mine")
    today = date.today()
    room, check_in, check_out = await _pick_available_room(client, today)

    assert (await _book(client, room["id"], check_in, check_out)).status_code == 201

    my = await client.get("/api/v1/bookings/my")
    assert my.status_code == 200
    assert len(my.json()) == 1


async def test_booking_requires_auth(client):
    today = date.today()
    check_in, check_out = _range(today)
    resp = await _book(client, 1, check_in, check_out)
    assert resp.status_code == 401


async def test_booking_idempotency_key_dedup(client):
    """接口幂等：相同 idempotency_key 重放应命中同一订单，不重复建单。"""
    await register_and_login(client, "booker_idem")
    today = date.today()
    room, check_in, check_out = await _pick_available_room(client, today)
    room_id = room["id"]

    key = "idem-key-0001"
    payload = {
        "room_id": room_id,
        "check_in": check_in,
        "check_out": check_out,
        "idempotency_key": key,
    }
    first = await client.post("/api/v1/bookings", json=payload)
    assert first.status_code == 201
    first_id = first.json()["id"]

    # 相同幂等键重放：应返回同一订单 id，而不是新建一条
    second = await client.post("/api/v1/bookings", json=payload)
    assert second.status_code == 201
    assert second.json()["id"] == first_id

    # 数据库中该幂等键只对应 1 条订单
    async with async_session_factory() as session:
        count = await session.execute(
            select(func.count()).select_from(Booking).where(Booking.idempotency_key == key)
        )
        assert count.scalar() == 1


async def test_concurrent_booking_same_room_no_oversell(client):
    """防超卖核心用例：N 个并发请求争抢同一房间同一日期，只能成功 1 个。"""
    await register_and_login(client, "booker_race")
    today = date.today()
    room, check_in, check_out = await _pick_available_room(client, today)
    room_id = room["id"]

    payload = {"room_id": room_id, "check_in": check_in, "check_out": check_out}
    results = await asyncio.gather(
        *[client.post("/api/v1/bookings", json=payload) for _ in range(8)]
    )

    statuses = [r.status_code for r in results]
    assert statuses.count(201) == 1, f"应恰好 1 个成功，实际状态码: {statuses}"
    assert all(s in (201, 409, 423) for s in statuses), f"失败状态应为 409/423: {statuses}"

    # 校验数据库最终状态：该房恰好 1 条订单、held 行数等于晚数（未超卖）
    async with async_session_factory() as session:
        booking_count = await session.execute(
            select(func.count()).select_from(Booking).where(Booking.room_id == room_id)
        )
        held_count = await session.execute(
            select(func.count())
            .select_from(DailyRoomInventory)
            .where(
                DailyRoomInventory.room_id == room_id,
                DailyRoomInventory.status == InventoryStatus.HELD,
            )
        )
        assert booking_count.scalar() == 1
        assert held_count.scalar() == NIGHTS