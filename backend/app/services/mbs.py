import json
import structlog
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.asset import AssetSnapshot, AssetRegistry
from app.models.session import SessionJournal
from app.models.prediction import CalibrationLog

logger = structlog.get_logger()

async def save_snapshot(db_session: AsyncSession, assets_data: list[dict]):
    """Batch insert snapshot data into asset_snapshots hypertable."""
    try:
        now = datetime.utcnow()
        snapshots = []
        for item in assets_data:
            snapshots.append(
                AssetSnapshot(
                    time=now,
                    symbol=item["symbol"],
                    price=item["price"],
                    zf_score=item["zf_score"],
                    psi_total=item["psi_total"],
                    d_res=item["d_res"],
                    oi=item.get("oi"),
                    funding_rate=item.get("funding_rate"),
                    volume_24h=item.get("volume_24h"),
                    bid_depth_ratio=item.get("bid_depth_ratio"),
                    ofi=item.get("ofi"),
                    mode=item["mode"],
                    status=item["status"],
                    predicted_change_pct=item.get("predicted_change_pct")
                )
            )

        db_session.add_all(snapshots)
        await db_session.commit()
        logger.info("MBS snapshot saved successfully", count=len(assets_data))
    except Exception as e:
        logger.error("Failed to save MBS snapshot", error=str(e))
        await db_session.rollback()
        raise

async def create_journal(db_session: AsyncSession, started_at: datetime, ended_at: datetime):
    """Summarize the trading session and create session_journals record."""
    try:
        logger.info("Creating session journal")

        # 1. Calculate avg zf_score across all snapshots in this session
        avg_score_res = await db_session.execute(
            select(AssetSnapshot.zf_score)
            .where(AssetSnapshot.time.between(started_at, ended_at))
        )
        scores = [r[0] for r in avg_score_res.all()]
        avg_zf_score = sum(scores) / len(scores) if scores else 0.0

        # 2. Count active Code Red symbols
        code_red_res = await db_session.execute(
            select(AssetSnapshot.symbol)
            .where(AssetSnapshot.status == "code_red")
            .where(AssetSnapshot.time.between(started_at, ended_at))
            .distinct()
        )
        code_red_count = len(code_red_res.all())

        # 3. Pull omega changes from calibration_log
        calib_res = await db_session.execute(
            select(CalibrationLog)
            .where(CalibrationLog.calibrated_at.between(started_at, ended_at))
            .order_by(CalibrationLog.calibrated_at.asc())
        )
        omega_logs = calib_res.scalars().all()
        omega_changes = []
        for log in omega_logs:
            omega_changes.append({
                "calibrated_at": log.calibrated_at.isoformat(),
                "omega_old": {"w1": log.omega_w1_old, "w2": log.omega_w2_old, "w3": log.omega_w3_old},
                "omega_new": {"w1": log.omega_w1_new, "w2": log.omega_w2_new, "w3": log.omega_w3_new}
            })

        # Create Journal
        journal = SessionJournal(
            started_at=started_at,
            ended_at=ended_at,
            avg_zf_score=round(avg_zf_score, 4),
            code_red_count=code_red_count,
            alerts_sent=0, # Will be incremented by alert module in Phase 3
            errors_count=0,
            omega_changes=omega_changes,
            summary=f"Session summarized from {started_at.isoformat()} to {ended_at.isoformat()}."
        )

        db_session.add(journal)
        await db_session.commit()
        logger.info("Session journal saved successfully", id=journal.id)
    except Exception as e:
        logger.error("Failed to create session journal", error=str(e))
        await db_session.rollback()
        raise

async def load_and_merge(db_session: AsyncSession) -> list[dict]:
    """Retrieve the latest snapshots and check for discrepancies."""
    try:
        logger.info("Loading and merging previous session state")

        # Get active registry symbols
        reg_result = await db_session.execute(
            select(AssetRegistry.symbol).where(AssetRegistry.is_active == True)
        )
        symbols = [r[0] for r in reg_result.all()]

        merged_data = []

        for symbol in symbols:
            # Get latest snapshot for each symbol
            snap_res = await db_session.execute(
                select(AssetSnapshot)
                .where(AssetSnapshot.symbol == symbol)
                .order_by(desc(AssetSnapshot.time))
                .limit(1)
            )
            snapshot = snap_res.scalar_one_or_none()
            if snapshot:
                merged_data.append({
                    "symbol": snapshot.symbol,
                    "price": float(snapshot.price),
                    "zf_score": snapshot.zf_score,
                    "psi_total": snapshot.psi_total,
                    "d_res": snapshot.d_res,
                    "oi": float(snapshot.oi) if snapshot.oi else None,
                    "funding_rate": snapshot.funding_rate,
                    "volume_24h": float(snapshot.volume_24h) if snapshot.volume_24h else None,
                    "bid_depth_ratio": snapshot.bid_depth_ratio,
                    "ofi": snapshot.ofi,
                    "mode": snapshot.mode,
                    "status": snapshot.status,
                    "predicted_change_pct": snapshot.predicted_change_pct
                })

        logger.info("Previous session state loaded", count=len(merged_data))
        return merged_data
    except Exception as e:
        logger.error("Failed to load and merge session states", error=str(e))
        raise
