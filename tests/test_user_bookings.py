"""User-facing bookings list pagination and delete tests."""

from datetime import date, timedelta

import pytest


@pytest.mark.asyncio
async def test_my_bookings_paginated(auth_client):
    resp = await auth_client.get("/api/v1/bookings/my?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["items"]) <= 5


@pytest.mark.asyncio
async def test_my_bookings_tab_filter(auth_client):
    resp = await auth_client.get("/api/v1/bookings/my?tab=cancelled&page=1&page_size=10")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "cancelled"


@pytest.mark.asyncio
async def test_delete_cancelled_booking(auth_client):
    rooms_resp = await auth_client.get(
        "/api/v1/rooms/search",
        params={
            "check_in": str(date.today() + timedelta(days=30)),
            "check_out": str(date.today() + timedelta(days=32)),
        },
    )
    assert rooms_resp.status_code == 200
    rooms = rooms_resp.json()
    if not rooms:
        pytest.skip("No available rooms for test window")

    create_resp = await auth_client.post(
        "/api/v1/bookings",
        json={
            "room_id": rooms[0]["id"],
            "check_in": str(date.today() + timedelta(days=30)),
            "check_out": str(date.today() + timedelta(days=32)),
        },
    )
    assert create_resp.status_code == 201
    booking_id = create_resp.json()["id"]

    cancel_resp = await auth_client.post(f"/api/v1/bookings/{booking_id}/cancel")
    assert cancel_resp.status_code == 200

    delete_resp = await auth_client.delete(f"/api/v1/bookings/{booking_id}")
    assert delete_resp.status_code == 200

    get_resp = await auth_client.get(f"/api/v1/bookings/{booking_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_confirmed_booking_forbidden(auth_client):
    rooms_resp = await auth_client.get(
        "/api/v1/rooms/search",
        params={
            "check_in": str(date.today() + timedelta(days=35)),
            "check_out": str(date.today() + timedelta(days=37)),
        },
    )
    if rooms_resp.status_code != 200 or not rooms_resp.json():
        pytest.skip("No available rooms for test window")

    create_resp = await auth_client.post(
        "/api/v1/bookings",
        json={
            "room_id": rooms_resp.json()[0]["id"],
            "check_in": str(date.today() + timedelta(days=35)),
            "check_out": str(date.today() + timedelta(days=37)),
        },
    )
    assert create_resp.status_code == 201
    booking_id = create_resp.json()["id"]

    pay_resp = await auth_client.post(f"/api/v1/bookings/{booking_id}/pay")
    assert pay_resp.status_code == 200

    delete_resp = await auth_client.delete(f"/api/v1/bookings/{booking_id}")
    assert delete_resp.status_code == 400
