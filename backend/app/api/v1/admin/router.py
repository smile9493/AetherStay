from fastapi import APIRouter

from app.api.v1.admin import bookings, inventory, room_types, rooms, stats, users

admin_router = APIRouter(prefix="/admin")
admin_router.include_router(bookings.router)
admin_router.include_router(rooms.router)
admin_router.include_router(room_types.router)
admin_router.include_router(stats.router)
admin_router.include_router(users.router)
admin_router.include_router(inventory.router)
