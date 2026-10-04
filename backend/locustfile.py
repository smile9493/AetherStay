"""Locust 压测脚本。

运行方式（在 backend 目录下）：
    locust -f locustfile.py --host http://localhost:8000 --headless -u 50 -r 10 -t 60s

其中 -u 并发用户数、-r 每秒孵化数、-t 持续时间。
"""

import random
from datetime import date, timedelta

from locust import HttpUser, between, task


class BookingUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # 复用 schema.sql 预置管理员账号，避免每次压测注册大量用户
        self.client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin1234"},
        )

    def _date_window(self):
        start = date.today() + timedelta(days=random.randint(1, 20))
        nights = random.randint(1, 5)
        return start, start + timedelta(days=nights)

    @task(3)
    def search_rooms(self):
        check_in, check_out = self._date_window()
        self.client.get(
            "/api/v1/rooms/search",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
            },
            name="/api/v1/rooms/search",
        )

    @task(1)
    def create_booking(self):
        check_in, check_out = self._date_window()
        resp = self.client.get(
            "/api/v1/rooms/search",
            params={"check_in": check_in.isoformat(), "check_out": check_out.isoformat()},
            name="/api/v1/rooms/search",
        )
        rooms = resp.json()
        if not rooms:
            return
        room_id = random.choice(rooms)["id"]
        self.client.post(
            "/api/v1/bookings",
            json={
                "room_id": room_id,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
            },
            name="/api/v1/bookings",
        )