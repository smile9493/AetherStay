"""客房接口测试：列表与可用房搜索。"""

from datetime import date, timedelta

from tests.conftest import register_and_login


async def test_list_rooms(client):
    resp = await client.get("/api/v1/rooms")
    assert resp.status_code == 200
    rooms = resp.json()
    assert len(rooms) == 4
    assert {r["room_number"] for r in rooms} == {"101", "102", "201", "301"}


async def test_search_available_rooms(client):
    check_in = (date.today() + timedelta(days=10)).isoformat()
    check_out = (date.today() + timedelta(days=13)).isoformat()
    resp = await client.get(
        "/api/v1/rooms/search",
        params={"check_in": check_in, "check_out": check_out},
    )
    assert resp.status_code == 200
    rooms = resp.json()
    assert len(rooms) == 4
    # 返回结构应包含房型与价格
    for r in rooms:
        assert r["status"] == "active"
        assert r["room_type"] is not None


async def test_search_invalid_range_returns_empty(client):
    check_in = (date.today() + timedelta(days=10)).isoformat()
    check_out = (date.today() + timedelta(days=8)).isoformat()
    resp = await client.get(
        "/api/v1/rooms/search",
        params={"check_in": check_in, "check_out": check_out},
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_search_requires_no_auth(client):
    """搜索为公开接口，未登录也能访问。"""
    check_in = (date.today() + timedelta(days=10)).isoformat()
    check_out = (date.today() + timedelta(days=13)).isoformat()
    resp = await client.get(
        "/api/v1/rooms/search",
        params={"check_in": check_in, "check_out": check_out},
    )
    assert resp.status_code == 200