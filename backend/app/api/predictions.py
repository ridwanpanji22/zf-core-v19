import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.asset import AssetRegistry
from app.models.prediction import PredictionLog

router = APIRouter()
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

@router.get("/top20")
async def get_top20_predictions(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve top 20 predicted assets with dynamic title based on market trend."""
    res = await db.execute(select(AssetRegistry.symbol).where(AssetRegistry.is_active == True))
    symbols = [r[0] for r in res.all()]

    if not symbols:
        symbols = settings.BOOTSTRAP_SYMBOLS

    assets = []
    up_count = 0
    down_count = 0

    for symbol in symbols:
        val = await redis_client.get(f"metrics:{symbol}")
        if val:
            metrics = json.loads(val)
            pred_res = await db.execute(
                select(PredictionLog.predicted_value)
                .where(PredictionLog.symbol == symbol)
                .order_by(PredictionLog.time.desc())
                .limit(1)
            )
            change_val = pred_res.scalar_one_or_none()
            predicted_change = change_val if change_val is not None else 0.0

            if predicted_change > 0:
                up_count += 1
            elif predicted_change < 0:
                down_count += 1

            assets.append({
                "symbol": symbol,
                "price": metrics.get("price", 0.0),
                "zf_score": metrics.get("zf_score", 0.0),
                "psi_total": metrics.get("psi_total", 0.0),
                "d_res": metrics.get("d_res", 0.0),
                "predicted_change_pct": predicted_change
            })

    total_predicted = up_count + down_count
    if total_predicted > 0:
        up_ratio = up_count / total_predicted
        down_ratio = down_count / total_predicted
    else:
        up_ratio, down_ratio = 0.5, 0.5

    if down_ratio > 0.60:
        title = "Pasar Dominan Turun — 20 Koin Prediksi Anjlok dalam 10 Hari"
        market_direction = "down"
    elif up_ratio > 0.60:
        title = "Pasar Dominan Naik — 20 Koin Prediksi Naik dalam 10 Hari"
        market_direction = "up"
    else:
        title = "Pasar Netral — 20 Koin dengan Potensi Pergerakan Tertinggi dalam 10 Hari"
        market_direction = "neutral"

    sorted_assets = sorted(assets, key=lambda x: abs(x["predicted_change_pct"]), reverse=True)
    top20 = sorted_assets[:20]

    for idx, item in enumerate(top20):
        item["rank"] = idx + 1

    return {
        "success": True,
        "data": {
            "title": title,
            "market_direction": market_direction,
            "assets": top20
        },
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }

# IMPORTANT: static routes MUST be defined before parameterized /{symbol}
@router.get("/analysis/market-dominance")
async def get_market_dominance(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Calculate percentage share of market directions."""
    res = await db.execute(select(AssetRegistry.symbol).where(AssetRegistry.is_active == True))
    symbols = [r[0] for r in res.all()]

    if not symbols:
        symbols = settings.BOOTSTRAP_SYMBOLS

    up_count = 0
    down_count = 0
    neutral_count = 0

    for symbol in symbols:
        pred_res = await db.execute(
            select(PredictionLog.predicted_value)
            .where(PredictionLog.symbol == symbol)
            .order_by(PredictionLog.time.desc())
            .limit(1)
        )
        change = pred_res.scalar_one_or_none()
        if change is None or abs(change) < 0.5:
            neutral_count += 1
        elif change > 0:
            up_count += 1
        else:
            down_count += 1

    total = len(symbols) if symbols else 1
    return {
        "success": True,
        "data": {
            "up_pct": round((up_count / total) * 100.0, 2),
            "down_pct": round((down_count / total) * 100.0, 2),
            "neutral_pct": round((neutral_count / total) * 100.0, 2)
        },
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }

@router.get("/{symbol}")
async def get_asset_prediction_detail(
    symbol: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve detailed predictions history for a single asset."""
    res = await db.execute(
        select(PredictionLog)
        .where(PredictionLog.symbol == symbol)
        .order_by(PredictionLog.time.desc())
        .limit(50)
    )
    rows = res.scalars().all()
    predictions = []
    for r in rows:
        predictions.append({
            "time": r.time.isoformat() + "Z",
            "prediction_type": r.prediction_type,
            "predicted_value": r.predicted_value,
            "actual_value": r.actual_value,
            "error": r.error,
            "omega_w1": r.omega_w1,
            "omega_w2": r.omega_w2,
            "omega_w3": r.omega_w3
        })

    return {
        "success": True,
        "data": predictions,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }
