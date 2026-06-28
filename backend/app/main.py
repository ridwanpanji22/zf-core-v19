from contextlib import asynccontextmanager
import asyncio
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import async_session_maker
from app.models.user import User
from sqlalchemy import select

# Import API routers
from app.api import assets, predictions, system, calibration, websocket, auth, admin, api_keys, demo

logger = structlog.get_logger()

# Global background tasks list to keep reference
bg_tasks = set()

async def seed_super_admin():
    """Seed super admin on application startup if none exists."""
    async with async_session_maker() as db:
        try:
            # 1. Check if any super admin exists
            res = await db.execute(select(User).where(User.role == "super_admin"))
            if res.scalar_one_or_none():
                logger.info("Super admin already exists, skipping seed")
                return

            # 2. If SUPER_ADMIN_EMAIL configured, seed it
            if settings.SUPER_ADMIN_EMAIL:
                admin_user = User(
                    email=settings.SUPER_ADMIN_EMAIL,
                    role="super_admin",
                    status="active"
                )
                db.add(admin_user)
                await db.commit()
                logger.info("Super admin seeded successfully", email=settings.SUPER_ADMIN_EMAIL)
        except Exception as e:
            logger.error("Failed to seed super admin", error=str(e))
            await db.rollback()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup lifecycle
    logger.info("ZF-Core initial startup", env=settings.APP_ENV)

    # Trigger super admin seed
    await seed_super_admin()

    # Start Redis WebSocket pub/sub listener task
    task = asyncio.create_task(websocket.redis_listener())
    bg_tasks.add(task)
    task.add_done_callback(bg_tasks.discard)

    yield

    # Shutdown lifecycle
    logger.info("ZF-Core graceful shutdown")
    for t in bg_tasks:
        t.cancel()

app = FastAPI(
    title="ZF-Core V19.0",
    version="19.0.0",
    lifespan=lifespan
)

# CORS middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production setup
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(api_keys.router, prefix="/api/user/api-keys", tags=["API Keys"])
app.include_router(demo.router, prefix="/api/demo", tags=["Demo"])
app.include_router(assets.router, prefix="/api/assets", tags=["Assets"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(calibration.router, prefix="/api/calibration", tags=["Calibration"])
app.include_router(websocket.router, tags=["WebSocket"])

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": app.version
    }
