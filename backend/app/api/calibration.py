from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models.prediction import CalibrationLog
from app.models.session import SystemEvent
from app.services.tasks import recalibrate_omega as trigger_task

router = APIRouter()

@router.get("/current")
async def get_current_calibration(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get latest calibration weights (omega w1, w2, w3)."""
    res = await db.execute(
        select(CalibrationLog)
        .order_by(CalibrationLog.calibrated_at.desc())
        .limit(1)
    )
    log = res.scalar_one_or_none()
    weights = {"w1": 0.35, "w2": 0.40, "w3": 0.25} if not log else {
        "w1": log.omega_w1_new, "w2": log.omega_w2_new, "w3": log.omega_w3_new
    }
    return {
        "success": True,
        "data": weights,
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.get("/history")
async def get_calibration_history(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve calibration history logs."""
    res = await db.execute(select(CalibrationLog).order_by(CalibrationLog.calibrated_at.desc()).limit(100))
    rows = res.scalars().all()
    data = []
    for r in rows:
        data.append({
            "id": r.id,
            "calibrated_at": r.calibrated_at.isoformat() + "Z",
            "omega_old": {"w1": r.omega_w1_old, "w2": r.omega_w2_old, "w3": r.omega_w3_old},
            "omega_new": {"w1": r.omega_w1_new, "w2": r.omega_w2_new, "w3": r.omega_w3_new},
            "avg_error_before": r.avg_error_before,
            "avg_error_after": r.avg_error_after,
            "samples_used": r.samples_used
        })
    return {
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.post("/trigger")
async def trigger_calibration(
    current_user = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger Celery recalibration task (Super Admin only)."""
    # Trigger celery task asynchronously
    trigger_task.delay()

    # Log to DB events
    event = SystemEvent(
        time=datetime.utcnow(),
        event_type="calibration_trigger",
        severity="info",
        details={"action": "recalibrate_manual", "admin_user_id": current_user.id}
    )
    db.add(event)
    await db.commit()

    return {
        "success": True,
        "data": {"status": "calibration_triggered"},
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
