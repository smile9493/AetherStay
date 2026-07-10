"""Admin rooms API tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_update_room_rejects_duplicate_number(admin_client):
    rooms_resp = await admin_client.get("/api/v1/admin/rooms?page=1&page_size=10")
    rooms = rooms_resp.json()["items"]
    assert len(rooms) >= 2

    target = rooms[0]
    taken_number = rooms[1]["room_number"]

    resp = await admin_client.put(
        f"/api/v1/admin/rooms/{target['id']}",
        json={"room_number": taken_number},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Room number already exists"


@pytest.mark.asyncio
async def test_admin_update_room_allows_unchanged_number(admin_client):
    rooms_resp = await admin_client.get("/api/v1/admin/rooms?page=1&page_size=1")
    room = rooms_resp.json()["items"][0]

    resp = await admin_client.put(
        f"/api/v1/admin/rooms/{room['id']}",
        json={"room_number": room["room_number"], "status": room["status"]},
    )
    assert resp.status_code == 200
    assert resp.json()["room_number"] == room["room_number"]


@pytest.mark.asyncio
async def test_admin_create_room_rejects_duplicate_number(admin_client):
    rooms_resp = await admin_client.get("/api/v1/admin/rooms?page=1&page_size=1")
    existing_number = rooms_resp.json()["items"][0]["room_number"]

    resp = await admin_client.post(
        "/api/v1/admin/rooms",
        json={
            "room_number": existing_number,
            "room_type_id": 1,
            "status": "active",
        },
    )
    assert resp.status_code == 409
