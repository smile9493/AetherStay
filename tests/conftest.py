"""Shared pytest fixtures for AetherStay integration tests."""

from __future__ import annotations

import os

# Must be set before importing app modules that create the DB engine
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_aetherstay.db"

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import Base, async_session_factory, engine
from app.main import create_app


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables in the SQLite database and seed test data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed minimal test data
    from datetime import date, timedelta

    from app.models.booking import BookingStatus
    from app.models.inventory import DailyRoomInventory, InventoryStatus
    from app.models.room import Room, RoomStatus, RoomType
    from app.models.user import User, UserRole
    from app.utils.auth import hash_password

    async with async_session_factory() as session:
        # Room types
        rt1 = RoomType(name="Standard Twin", base_price=299.00, capacity=2, total_rooms=3,
                       description="Comfortable twin room", amenities="WiFi,TV,AC", image_url="https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80")
        rt2 = RoomType(name="Deluxe King", base_price=499.00, capacity=2, total_rooms=2,
                       description="Spacious king bed room", amenities="WiFi,TV,AC,Minibar", image_url="https://images.unsplash.com/photo-1611892440504-42a792e56d4b?w=800&q=80")
        rt3 = RoomType(name="Executive Suite", base_price=899.00, capacity=4, total_rooms=2,
                       description="Luxury suite with living room", amenities="WiFi,TV,AC,Bathtub,Coffee", image_url="https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80")
        session.add_all([rt1, rt2, rt3])
        await session.flush()

        # Rooms
        rooms_data = [
            ("101", rt1.id), ("102", rt1.id), ("103", rt1.id),
            ("201", rt2.id), ("202", rt2.id),
            ("301", rt3.id), ("302", rt3.id),
        ]
        rooms = []
        for num, tid in rooms_data:
            room = Room(room_number=num, room_type_id=tid, status=RoomStatus.ACTIVE)
            session.add(room)
            rooms.append(room)
        await session.flush()

        # Generate 90 days of inventory
        today = date.today()
        for room in rooms:
            for day_offset in range(90):
                inv_date = today + timedelta(days=day_offset)
                inv = DailyRoomInventory(
                    room_id=room.id,
                    date=inv_date,
                    status=InventoryStatus.AVAILABLE,
                )
                session.add(inv)
        await session.flush()

        # Default admin user
        admin = User(
            username="admin",
            password_hash=hash_password("admin1234"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin)
        await session.flush()

        from app.services.settings_service import seed_default_settings
        await seed_default_settings(session)

        await session.commit()

    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    if os.path.exists("./test_aetherstay.db"):
        os.remove("./test_aetherstay.db")
    for ext in ("-wal", "-shm"):
        p = f"./test_aetherstay.db{ext}"
        if os.path.exists(p):
            os.remove(p)


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client):
    """HTTP client with a freshly registered authenticated user."""
    username = f"api_{uuid.uuid4().hex[:8]}"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"username": username, "password": password})
    await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    return client


@pytest_asyncio.fixture
async def admin_client(client):
    """HTTP client authenticated as the seeded admin user."""
    await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin1234"})
    return client
