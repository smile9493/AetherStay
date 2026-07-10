"""Admin stats API tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_stats_success(admin_client):
    """Admin can fetch aggregated dashboard stats."""
    resp = await admin_client.get("/api/v1/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_bookings" in data
    assert "pending_bookings" in data
    assert "confirmed_bookings" in data
    assert "active_check_ins" in data
    assert "total_revenue" in data
    assert "total_rooms" in data
    assert "active_rooms" in data
    assert "total_users" in data
    assert "active_users" in data
    assert data["total_rooms"] >= 7
    assert data["total_users"] >= 1


@pytest.mark.asyncio
async def test_admin_stats_forbidden_for_customer(auth_client):
    """Non-admin users cannot access admin stats."""
    resp = await auth_client.get("/api/v1/admin/stats")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats_unauthenticated(client):
    """Unauthenticated requests are rejected."""
    resp = await client.get("/api/v1/admin/stats")
    assert resp.status_code == 401
