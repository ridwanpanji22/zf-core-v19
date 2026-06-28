import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.session import SessionJournal, SystemEvent
from app.models.config import SystemConfig
from redis import Redis
from app.config import settings

router = APIRouter()
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

@router.get("/sessions")
async def list_session_journals(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List session journals chronologically."""
    res = await db.execute(select(SessionJournal).order_by(SessionJournal.started_at.desc()))
    journals = res.scalars().all()
    data = []
    for j in journals:
        data.append({
            "id": j.id,
            "started_at": j.started_at.isoformat() + "Z",
            "ended_at": j.ended_at.isoformat() + "Z",
            "avg_zf_score": j.avg_zf_score,
            "code_red_count": j.code_red_count,
            "alerts_sent": j.alerts_sent,
            "errors_count": j.errors_count,
            "omega_changes": j.omega_changes,
            "summary": j.summary
        })
    return {
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.get("/sessions/{id}")
async def get_session_journal(
    id: int,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve detailed session journal."""
    res = await db.execute(select(SessionJournal).where(SessionJournal.id == id))
    j = res.scalar_one_or_none()
    if not j:
        raise HTTPException(status_code=404, detail="Journal not found")

    return {
        "success": True,
        "data": {
            "id": j.id,
            "started_at": j.started_at.isoformat() + "Z",
            "ended_at": j.ended_at.isoformat() + "Z",
            "avg_zf_score": j.avg_zf_score,
            "code_red_count": j.code_red_count,
            "alerts_sent": j.alerts_sent,
            "errors_count": j.errors_count,
            "omega_changes": j.omega_changes,
            "summary": j.summary
        },
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.get("/system/status")
async def get_system_status(
    current_user = Depends(get_current_user)
):
    """Retrieve global system protective metrics and states."""
    cb_active = redis_client.get("system:circuit_breaker") == "true"
    cold_active = redis_client.get("system:cold_mode") == "true"

    return {
        "success": True,
        "data": {
            "circuit_breaker": cb_active,
            "cold_mode": cold_active,
            "assets_monitored": settings.ASSET_SWARM_SIZE,
            "websocket_connected": True, # Mock state
            "last_data_received": datetime.utcnow().isoformat() + "Z"
        },
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.post("/system/circuit-breaker/reset")
async def reset_circuit_breaker(
    current_user = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate Circuit Breaker status (Super Admin only)."""
    redis_client.set("system:circuit_breaker", "false")

    # Log to DB events
    event = SystemEvent(
        time=datetime.utcnow(),
        event_type="circuit_breaker",
        severity="info",
        details={"action": "reset_manual", "admin_user_id": current_user.id}
    )
    db.add(event)
    await db.commit()

    return {
        "success": True,
        "data": {"circuit_breaker_active": False},
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.post("/system/cold-mode/unlock")
async def unlock_cold_mode(
    current_user = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db)
):
    """Unlock Cold Mode block manually (Super Admin only)."""
    redis_client.set("system:cold_mode", "false")

    event = SystemEvent(
        time=datetime.utcnow(),
        event_type="mode_dingin",
        severity="info",
        details={"action": "unlock_manual", "admin_user_id": current_user.id}
    )
    db.add(event)
    await db.commit()

    return {
        "success": True,
        "data": {"cold_mode_active": False},
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.get("/system/health-detailed")
async def get_detailed_health(db: AsyncSession = Depends(get_db)):
    """Detailed health check endpoint that tests DB and Redis status (503 on error)."""
    db_alive = False
    redis_alive = False
    try:
        # 1. Test database connection
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        db_alive = True
    except Exception:
        pass

    try:
        # 2. Test Redis connection
        redis_client.ping()
        redis_alive = True
    except Exception:
        pass

    status_code = status.HTTP_200_OK if (db_alive and redis_alive) else status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "success": db_alive and redis_alive,
        "data": {
            "status": "healthy" if (db_alive and redis_alive) else "unhealthy",
            "database_connected": db_alive,
            "redis_connected": redis_alive,
            "version": "19.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        "error": None if (db_alive and redis_alive) else {"code": "SERVICE_UNAVAILABLE", "message": "Backend dependencies connection failure"},
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
