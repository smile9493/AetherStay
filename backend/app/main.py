from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.tasks.auto_checkout import auto_checkout_due_bookings_task
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
        auto_checkout_due_bookings_task,
        "interval",
        minutes=settings.AUTO_CHECKOUT_INTERVAL_MINUTES,
        id="auto_checkout_due_bookings",
        replace_existing=True,
    )
    scheduler.start()
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
        # 采用 Streamable HTTP 传输（MCP 现代传输方式，挂载于 /mcp），
        # 供 Claude Desktop / Cursor / 兼容 MCP 协议的 Agent 客户端调用。
        mcp.mount_http()
    except ImportError:
        pass

    return app


app = create_app()
