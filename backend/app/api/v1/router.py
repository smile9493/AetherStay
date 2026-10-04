from fastapi import APIRouter

from app.api.v1 import agent, auth, bookings, payments, rooms
from app.api.v1.admin.router import admin_router

api_router = APIRouter()
api_router.include_router(agent.router)
api_router.include_router(auth.router)
api_router.include_router(rooms.router)
api_router.include_router(bookings.router)
api_router.include_router(payments.router)
api_router.include_router(admin_router)
