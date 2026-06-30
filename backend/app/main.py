import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import select, text

# Import API routers
from app.api import admin, api_keys, assets, auth, calibration, demo, predictions, system, websocket
from app.config import settings
from app.database import async_session_maker
from app.models.user import User

logger = structlog.get_logger()

# Rate limiter — 200 req/min per IP (global default)
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# Global background tasks list to keep reference
bg_tasks = set()

def _validate_production_secrets():
    """Fail-fast if production uses default secrets."""
    if settings.APP_ENV != "production":
        return
    for name, val in [
        ("JWT_SECRET", settings.JWT_SECRET),
        ("DB_PASSWORD", settings.DB_PASSWORD),
        ("API_KEY_ENCRYPTION_SECRET", settings.API_KEY_ENCRYPTION_SECRET),
        ("REDIS_PASSWORD", settings.REDIS_PASSWORD),
    ]:
        if "changeme" in val.lower():
            raise RuntimeError(
                f"FATAL: {name} still contains default value. "
                f"Set a secure random string in .env before running in production."
            )

async def seed_super_admin():
    """Seed super admin on application startup if none exists."""
    async with async_session_maker() as db:
        try:
            res = await db.execute(select(User).where(User.role == "super_admin"))
            if res.scalar_one_or_none():
                logger.info("Super admin already exists, skipping seed")
                return

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
    # Validate secrets before anything else
    _validate_production_secrets()

    logger.info("ZF-Core initial startup", env=settings.APP_ENV)

    await seed_super_admin()

    # Start Redis pub/sub listener for WebSocket broadcast
    task = asyncio.create_task(websocket.redis_listener())
    bg_tasks.add(task)
    task.add_done_callback(bg_tasks.discard)

    # Start OKX WebSocket data ingestion
    from app.ingestion.okx_ws import OKXWebSocketClient
    from app.core.asset_swarm import AssetSwarmManager

    okx_client = OKXWebSocketClient()

    async def start_ingestion():
        """Load active symbols from DB (or use defaults) and start OKX WS."""
        try:
            swarm = AssetSwarmManager()
            async with async_session_maker() as db:
                from app.models import AssetRegistry
                from sqlalchemy import select as sa_select
                res = await db.execute(sa_select(AssetRegistry.symbol).where(AssetRegistry.is_active == True))
                symbols = [r[0] for r in res.all()]

            if not symbols:
                # No assets in DB yet — use top perpetuals as bootstrap
                symbols = [
                    "BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP",
                    "XRP-USDT-SWAP", "DOGE-USDT-SWAP", "ADA-USDT-SWAP",
                    "AVAX-USDT-SWAP", "DOT-USDT-SWAP", "LINK-USDT-SWAP",
                    "MATIC-USDT-SWAP",
                ]
                logger.info("No assets in registry, using bootstrap symbols", count=len(symbols))

            await okx_client.start(symbols)
            logger.info("OKX WebSocket ingestion started", symbols=len(symbols))
        except Exception as e:
            logger.error("Failed to start OKX ingestion — dashboard will show stale data", error=str(e))

    ingestion_task = asyncio.create_task(start_ingestion())
    bg_tasks.add(ingestion_task)
    ingestion_task.add_done_callback(bg_tasks.discard)

    yield

    logger.info("ZF-Core graceful shutdown")
    await okx_client.stop()
    for t in bg_tasks:
        t.cancel()

app = FastAPI(
    title="ZF-Core V19.0",
    version="19.0.0",
    lifespan=lifespan
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS — restrict to configured frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler — never leak stack traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", path=request.url.path, error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": {"message": "Internal server error"},
        }
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
    """Deep health check — verifies DB and Redis connectivity."""
    checks = {"db": "ok", "redis": "ok"}
    try:
        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        checks["db"] = "error"
    try:
        from redis.asyncio import Redis as AsyncRedis
        r = AsyncRedis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
    except Exception:
        checks["redis"] = "error"

    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "healthy" if healthy else "degraded", "version": app.version, "checks": checks}
    )
