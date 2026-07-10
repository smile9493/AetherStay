"""
Locust load tests for AetherStay booking concurrency.

Scenarios:
  S1 - Oversell protection: many users book the same room/dates concurrently
  S2 - Mixed search + booking traffic

Usage:
  pip install -r tests/requirements-dev.txt
  locust -f tests/load/locustfile.py --host=http://localhost:8000

Headless S1 example:
  locust -f tests/load/locustfile.py --host=http://localhost:8000 \\
    --headless -u 30 -r 10 -t 30s --tags s1
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from locust import HttpUser, between, events, tag, task

# Shared target for S1 contention scenario (set in test_start)
TARGET: dict = {
    "room_id": None,
    "check_in": None,
    "check_out": None,
}

# Counters for summary
STATS: dict = {
    "success_hold": 0,
    "lock_conflict": 0,
    "other_error": 0,
}


def _future_dates(offset_days: int = 60) -> tuple[str, str]:
    start = date.today() + timedelta(days=offset_days)
    end = start + timedelta(days=2)
    return start.isoformat(), end.isoformat()


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Discover an available room for contention tests."""
    import httpx

    host = environment.host or "http://localhost:8000"
    check_in, check_out = _future_dates(30)
    try:
        with httpx.Client(base_url=host, timeout=10.0) as client:
            resp = client.get(
                "/api/v1/rooms/search",
                params={"check_in": check_in, "check_out": check_out},
            )
            if resp.status_code == 200:
                rooms = resp.json()
                if rooms:
                    TARGET["room_id"] = rooms[0]["id"]
                    TARGET["check_in"] = check_in
                    TARGET["check_out"] = check_out
                    print(f"[setup] S1 target: room_id={TARGET['room_id']} {check_in} -> {check_out}")
    except Exception as exc:
        print(f"[setup] Failed to discover S1 target: {exc}")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, exception, **kwargs):
    if "POST /api/v1/bookings [S1]" not in name:
        return
    if exception:
        err = str(exception)
        if "423" in err or "409" in err:
            STATS["lock_conflict"] += 1
        else:
            STATS["other_error"] += 1
        return
    if response is None:
        return
    if response.status_code == 201:
        STATS["success_hold"] += 1
    elif response.status_code in (423, 409):
        STATS["lock_conflict"] += 1
    else:
        STATS["other_error"] += 1


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    total = STATS["success_hold"] + STATS["lock_conflict"] + STATS["other_error"]
    print("\n=== S1 Booking Contention Summary ===")
    print(f"  201 success_hold:   {STATS['success_hold']}")
    print(f"  423/409 conflicts:  {STATS['lock_conflict']}")
    print(f"  other errors:       {STATS['other_error']}")
    print(f"  total booking reqs: {total}")
    if STATS["success_hold"] > 1:
        print("  WARNING: more than one 201 — investigate oversell risk")


class BookingLoadUser(HttpUser):
    """Simulates authenticated users searching and booking rooms."""

    wait_time = between(0.1, 0.8)

    def on_start(self):
        suffix = uuid.uuid4().hex[:8]
        username = f"locust_{suffix}"
        password = "locust1234"
        self.client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": password},
            name="/api/v1/auth/register",
        )
        self.client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
            name="/api/v1/auth/login",
        )

    @task(5)
    @tag("s2", "search")
    def search_rooms(self):
        check_in, check_out = _future_dates(45)
        self.client.get(
            f"/api/v1/rooms/search?check_in={check_in}&check_out={check_out}",
            name="/api/v1/rooms/search [S2]",
        )

    @task(1)
    @tag("s1", "booking")
    def book_same_room(self):
        if not TARGET["room_id"]:
            return
        self.client.post(
            "/api/v1/bookings",
            json={
                "room_id": TARGET["room_id"],
                "check_in": TARGET["check_in"],
                "check_out": TARGET["check_out"],
            },
            name="POST /api/v1/bookings [S1]",
        )

    @task(1)
    @tag("s2", "booking")
    def book_random_room(self):
        check_in, check_out = _future_dates(50)
        resp = self.client.get(
            f"/api/v1/rooms/search?check_in={check_in}&check_out={check_out}",
            name="/api/v1/rooms/search [S2-pick]",
        )
        if resp.status_code != 200:
            return
        rooms = resp.json()
        if not rooms:
            return
        room = rooms[0]
        self.client.post(
            "/api/v1/bookings",
            json={
                "room_id": room["id"],
                "check_in": check_in,
                "check_out": check_out,
            },
            name="POST /api/v1/bookings [S2]",
        )
