"""Admin users detail and membership tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_get_user_detail(admin_client, client):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "member_test_user", "password": "testpass123"},
    )
    users_resp = await admin_client.get("/api/v1/admin/users?page=1&page_size=100")
    user = next(u for u in users_resp.json()["items"] if u["username"] == "member_test_user")

    detail_resp = await admin_client.get(f"/api/v1/admin/users/{user['id']}")
    assert detail_resp.status_code == 200
    data = detail_resp.json()
    assert data["username"] == "member_test_user"
    assert data["membership_tier"] == "standard"
    assert "stats" in data
    assert data["stats"]["total_bookings"] >= 0


@pytest.mark.asyncio
async def test_admin_update_user_membership(admin_client, client):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "member_upgrade_user", "password": "testpass123"},
    )
    users_resp = await admin_client.get("/api/v1/admin/users?page=1&page_size=100")
    user = next(u for u in users_resp.json()["items"] if u["username"] == "member_upgrade_user")

    update_resp = await admin_client.put(
        f"/api/v1/admin/users/{user['id']}",
        json={
            "display_name": "金卡贵宾",
            "membership_tier": "gold",
            "membership_points": 1200,
            "phone": "13800138000",
            "admin_notes": "VIP客户",
        },
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["display_name"] == "金卡贵宾"
    assert data["membership_tier"] == "gold"
    assert data["membership_points"] == 1200
    assert data["admin_notes"] == "VIP客户"


@pytest.mark.asyncio
async def test_admin_filter_users_by_tier(admin_client, client):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "silver_member_user", "password": "testpass123"},
    )
    users_resp = await admin_client.get("/api/v1/admin/users?page=1&page_size=100")
    user = next(u for u in users_resp.json()["items"] if u["username"] == "silver_member_user")

    await admin_client.put(
        f"/api/v1/admin/users/{user['id']}",
        json={"membership_tier": "silver"},
    )

    filtered = await admin_client.get("/api/v1/admin/users?membership_tier=silver&page_size=100")
    assert filtered.status_code == 200
    ids = [u["id"] for u in filtered.json()["items"]]
    assert user["id"] in ids
