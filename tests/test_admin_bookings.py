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
