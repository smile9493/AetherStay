from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.database import async_session_factory
from app.services import booking_service
from app.tasks.auto_checkout import auto_checkout_task
from app.tasks.hold_release import release_expired_holds_task

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        release_expired_holds_task,
        "interval",
        minutes=settings.HOLD_RELEASE_INTERVAL_MINUTES,
        id="release_expired_holds",
        replace_existing=True,
    )
    scheduler.add_job(
        auto_checkout_task,
        "interval",
        minutes=1,
        id="auto_checkout",
        replace_existing=True,
    )
    scheduler.start()
    async with async_session_factory() as db:
        released = await booking_service.reconcile_stale_inventory(db)
        if released:
            import logging
            logging.getLogger(__name__).info("Reconciled %d stale inventory row(s)", released)
    yield
    scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Hotel room booking management system with MCP support",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

    try:
        from fastapi_mcp import FastApiMCP

        mcp = FastApiMCP(app)
        mcp.mount()
    except ImportError:
        pass

    return app


app = create_app()
