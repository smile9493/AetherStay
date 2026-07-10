"""Admin bookings list pagination tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_bookings_paginated(admin_client):
    resp = await admin_client.get("/api/v1/admin/bookings?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 10


@pytest.mark.asyncio
async def test_admin_bookings_filter_and_page(admin_client):
    resp = await admin_client.get(
        "/api/v1/admin/bookings",
        params={"status": "cancelled", "page": 1, "page_size": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["page_size"] == 5
    for item in data["items"]:
        assert item["status"] == "cancelled"


@pytest.mark.asyncio
async def test_admin_bookings_forbidden_for_customer(auth_client):
    resp = await auth_client.get("/api/v1/admin/bookings")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_users_paginated(admin_client):
    resp = await admin_client.get("/api/v1/admin/users?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) <= 10


@pytest.mark.asyncio
async def test_admin_rooms_paginated(admin_client):
    resp = await admin_client.get("/api/v1/admin/rooms?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["page_size"] == 5


@pytest.mark.asyncio
async def test_admin_room_types_paginated(admin_client):
    resp = await admin_client.get("/api/v1/admin/room-types?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_admin_inventory_paginated(admin_client):
    resp = await admin_client.get("/api/v1/admin/inventory?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "rooms" in data
    assert "total" in data
    assert len(data["rooms"]) <= 5


@pytest.mark.asyncio
async def test_admin_create_and_edit_booking(admin_client, client):
    username = "walkin_guest"
    await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "testpass123"},
    )
    users_resp = await admin_client.get("/api/v1/admin/users?page=1&page_size=100")
    user = next(u for u in users_resp.json()["items"] if u["username"] == username)

    from datetime import date, timedelta

    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)

    rooms_resp = await client.get(
        "/api/v1/rooms/search",
        params={"check_in": check_in.isoformat(), "check_out": check_out.isoformat()},
    )
    room_id = rooms_resp.json()[0]["id"]

    create_resp = await admin_client.post(
        "/api/v1/admin/bookings",
        json={
            "user_id": user["id"],
            "room_id": room_id,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "notes": "前台代客",
            "auto_confirm": True,
        },
    )
    assert create_resp.status_code == 201
    booking = create_resp.json()
    assert booking["status"] == "confirmed"
    assert booking["notes"] == "前台代客"

    new_check_out = check_out + timedelta(days=1)
    update_resp = await admin_client.put(
        f"/api/v1/admin/bookings/{booking['id']}",
        json={"notes": "已延期一天", "check_out": new_check_out.isoformat()},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["notes"] == "已延期一天"
    assert updated["check_out"] == new_check_out.isoformat()


@pytest.mark.asyncio
async def test_admin_change_booking_room(admin_client, client):
    username = "room_change_guest"
    await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "testpass123"},
    )
    users_resp = await admin_client.get("/api/v1/admin/users?page=1&page_size=100")
    user = next(u for u in users_resp.json()["items"] if u["username"] == username)

    from datetime import date, timedelta

    check_in = date.today() + timedelta(days=20)
    check_out = check_in + timedelta(days=1)

    rooms_resp = await client.get(
        "/api/v1/rooms/search",
        params={"check_in": check_in.isoformat(), "check_out": check_out.isoformat()},
    )
    rooms = rooms_resp.json()
    assert len(rooms) >= 2
    room_a, room_b = rooms[0]["id"], rooms[1]["id"]

    create_resp = await admin_client.post(
        "/api/v1/admin/bookings",
        json={
            "user_id": user["id"],
            "room_id": room_a,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "auto_confirm": True,
        },
    )
    booking_id = create_resp.json()["id"]

    change_resp = await admin_client.put(
        f"/api/v1/admin/bookings/{booking_id}/room",
        json={"room_id": room_b},
    )
    assert change_resp.status_code == 200
    assert change_resp.json()["room_id"] == room_b


@pytest.mark.asyncio
async def test_admin_booking_forbidden_for_customer(auth_client):
    resp = await auth_client.post(
        "/api/v1/admin/bookings",
        json={
            "user_id": 1,
            "room_id": 1,
            "check_in": "2099-01-01",
            "check_out": "2099-01-02",
        },
    )
    assert resp.status_code == 403
