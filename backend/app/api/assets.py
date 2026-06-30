import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.asset import AssetRegistry, AssetSnapshot

router = APIRouter()
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

@router.get("")
async def list_assets(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List 200 assets with their latest metrics (cached in Redis, fallback DB)."""
    res = await db.execute(select(AssetRegistry.symbol).where(AssetRegistry.is_active == True))
    symbols = [r[0] for r in res.all()]

    if not symbols:
        symbols = settings.BOOTSTRAP_SYMBOLS

    assets = []
    for symbol in symbols:
        val = await redis_client.get(f"metrics:{symbol}")
        if val:
            assets.append(json.loads(val))
        else:
            assets.append({
                "symbol": symbol,
                "price": 0.0,
                "zf_score": 0.0,
                "psi_total": 0.0,
                "d_res": 0.0,
                "status": "normal",
                "mode": "heartbeat"
            })

    assets_sorted = sorted(assets, key=lambda x: x.get("zf_score", 0.0), reverse=True)

    return {
        "success": True,
        "data": assets_sorted,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }

@router.get("/{symbol}")
async def get_asset_detail(
    symbol: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve detailed metadata for a single asset."""
    res = await db.execute(select(AssetRegistry).where(AssetRegistry.symbol == symbol))
    asset = res.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    val = await redis_client.get(f"metrics:{symbol}")
    metrics = json.loads(val) if val else {
        "price": 0.0, "zf_score": 0.0, "psi_total": 0.0, "d_res": 0.0, "status": "normal", "mode": "heartbeat"
    }

    data = {
        "symbol": asset.symbol,
        "base_currency": asset.base_currency,
        "cluster_id": asset.cluster_id,
        "dampening_factor": asset.dampening_factor,
        "is_active": asset.is_active,
        **metrics
    }

    return {
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }

@router.get("/{symbol}/history")
async def get_asset_history(
    symbol: str,
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve historical snapshots for charts."""
    res = await db.execute(
        select(AssetSnapshot)
        .where(AssetSnapshot.symbol == symbol)
        .order_by(AssetSnapshot.time.desc())
        .limit(limit)
    )
    rows = res.scalars().all()
    history = []
    for r in rows:
        history.append({
            "time": r.time.isoformat() + "Z",
            "price": float(r.price),
            "zf_score": r.zf_score,
            "psi_total": r.psi_total,
            "d_res": r.d_res,
            "funding_rate": r.funding_rate,
            "volume_24h": float(r.volume_24h) if r.volume_24h else None
        })

    return {
        "success": True,
        "data": history[::-1], # chronological order
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }

@router.get("/{symbol}/orderbook")
async def get_orderbook(
    symbol: str,
    current_user = Depends(get_current_user)
):
    """Get active orderbook depth analysis."""
    val = await redis_client.get(f"book:{symbol}")
    if not val:
        return {
            "success": True,
            "data": {"bids": [], "asks": [], "bid_depth_ratio": 1.0},
            "error": None,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }

    book = json.loads(val)
    bids = [[float(x[0]), float(x[1])] for x in book["data"]["bids"]]
    asks = [[float(x[0]), float(x[1])] for x in book["data"]["asks"]]

    bids_vol = sum(x[1] for x in bids)
    asks_vol = sum(x[1] for x in asks)
    ratio = bids_vol / asks_vol if asks_vol > 0 else 1.0

    return {
        "success": True,
        "data": {
            "bids": bids,
            "asks": asks,
            "bid_depth_ratio": round(ratio, 2)
        },
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }

@router.get("/{symbol}/liquidation-map")
async def get_liquidation_map(
    symbol: str,
    current_user = Depends(get_current_user)
):
    """Simulate liquidation zones representation map."""
    # ponytail: Phase 1 MVP — mock data around current price. Replace with real
    #   liquidation data from OKX when execution engine is active (Phase 3).
    val = await redis_client.get(f"tick:{symbol}")
    price = 60000.0
    if val:
        try:
            price = float(json.loads(val)["data"]["last"])
        except Exception:
            pass

    clusters = [
        {"price": round(price * 0.99, 2), "volume": 1500000.0, "side": "buy"},
        {"price": round(price * 0.98, 2), "volume": 3200000.0, "side": "buy"},
        {"price": round(price * 1.01, 2), "volume": 1800000.0, "side": "sell"},
        {"price": round(price * 1.02, 2), "volume": 4100000.0, "side": "sell"}
    ]

    return {
        "success": True,
        "data": clusters,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }
