import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_user
from app.services import demo as demo_service
from app.models.demo import DemoPosition
from redis import Redis
from app.config import settings
from pydantic import BaseModel, Field

router = APIRouter()
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

class OpenPositionRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    side: str = Field(..., pattern="^(long|short)$")
    size_usdt: float = Field(..., gt=0)
    leverage: int = Field(..., ge=1)

@router.get("/wallet")
async def get_wallet(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve demo wallet metrics, statistics, and unrealized PnL."""
    wallet = await demo_service.get_or_create_wallet(db, current_user.id)

    # Calculate current open positions unrealized PnL
    pos_res = await db.execute(
        select(DemoPosition)
        .where(DemoPosition.user_id == current_user.id)
        .where(DemoPosition.status == "open")
    )
    open_positions = pos_res.scalars().all()

    unrealized_pnl = 0.0
    for pos in open_positions:
        val = redis_client.get(f"metrics:{pos.symbol}")
        if val:
            try:
                price = float(json.loads(val)["price"])
                entry = float(pos.entry_price)
                size = float(pos.size_usdt)
                if pos.side == "long":
                    unrealized_pnl += ((price - entry) / entry) * size
                else:
                    unrealized_pnl += ((entry - price) / entry) * size
            except Exception:
                pass

    win_rate = (wallet.win_trades / wallet.total_trades * 100.0) if wallet.total_trades > 0 else 0.0

    return {
        "success": True,
        "data": {
            "balance": float(wallet.balance),
            "initial_balance": float(wallet.initial_balance),
            "total_pnl": float(wallet.total_pnl),
            "total_trades": wallet.total_trades,
            "win_trades": wallet.win_trades,
            "win_rate": round(win_rate, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "last_reset_at": wallet.last_reset_at.isoformat() + "Z"
        },
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.post("/wallet/reset")
async def reset_demo_wallet(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reset virtual wallet balance to default config."""
    wallet = await demo_service.reset_wallet(db, current_user.id)
    return {
        "success": True,
        "data": {
            "balance": float(wallet.balance),
            "total_pnl": float(wallet.total_pnl),
            "total_trades": wallet.total_trades,
            "win_trades": wallet.win_trades
        },
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.get("/positions")
async def get_open_positions(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List open positions with real-time unrealized PnL."""
    res = await db.execute(
        select(DemoPosition)
        .where(DemoPosition.user_id == current_user.id)
        .where(DemoPosition.status == "open")
    )
    positions = res.scalars().all()

    data = []
    for pos in positions:
        val = redis_client.get(f"metrics:{pos.symbol}")
        unrealized = 0.0
        mark_price = float(pos.entry_price)
        if val:
            try:
                mark_price = float(json.loads(val)["price"])
                entry = float(pos.entry_price)
                size = float(pos.size_usdt)
                if pos.side == "long":
                    unrealized = ((mark_price - entry) / entry) * size
                else:
                    unrealized = ((entry - mark_price) / entry) * size
            except Exception:
                pass

        data.append({
            "id": pos.id,
            "symbol": pos.symbol,
            "side": pos.side,
            "size_usdt": float(pos.size_usdt),
            "leverage": pos.leverage,
            "entry_price": float(pos.entry_price),
            "mark_price": mark_price,
            "margin": float(pos.margin),
            "fee": float(pos.fee) if pos.fee else 0.0,
            "unrealized_pnl": round(unrealized, 2),
            "opened_at": pos.opened_at.isoformat() + "Z"
        })
    return {
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.post("/positions")
async def open_virtual_position(
    payload: OpenPositionRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Open new paper position."""
    try:
        pos = await demo_service.open_position(
            db=db,
            user_id=current_user.id,
            symbol=payload.symbol,
            side=payload.side,
            size_usdt=payload.size_usdt,
            leverage=payload.leverage
        )
        return {
            "success": True,
            "data": {
                "id": pos.id,
                "symbol": pos.symbol,
                "side": pos.side,
                "size_usdt": float(pos.size_usdt),
                "leverage": pos.leverage,
                "entry_price": float(pos.entry_price),
                "margin": float(pos.margin),
                "fee": float(pos.fee) if pos.fee else 0.0,
                "opened_at": pos.opened_at.isoformat() + "Z"
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/positions/{id}/close")
async def close_virtual_position(
    id: int,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Close virtual position manually."""
    try:
        pos = await demo_service.close_position(db, current_user.id, id, reason="manual")
        return {
            "success": True,
            "data": {
                "id": pos.id,
                "symbol": pos.symbol,
                "side": pos.side,
                "exit_price": float(pos.exit_price) if pos.exit_price else None,
                "pnl": float(pos.pnl) if pos.pnl is not None else 0.0,
                "fee": float(pos.fee) if pos.fee else 0.0,
                "status": pos.status,
                "close_reason": pos.close_reason,
                "closed_at": pos.closed_at.isoformat() + "Z" if pos.closed_at else None
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history")
async def get_demo_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve historical demo trades list."""
    offset = (page - 1) * limit
    res = await db.execute(
        select(DemoPosition)
        .where(DemoPosition.user_id == current_user.id)
        .where(DemoPosition.status == "closed")
        .order_by(DemoPosition.closed_at.desc())
        .offset(offset)
        .limit(limit)
    )
    positions = res.scalars().all()
    data = []
    for pos in positions:
        data.append({
            "id": pos.id,
            "symbol": pos.symbol,
            "side": pos.side,
            "size_usdt": float(pos.size_usdt),
            "leverage": pos.leverage,
            "entry_price": float(pos.entry_price),
            "exit_price": float(pos.exit_price) if pos.exit_price else None,
            "margin": float(pos.margin),
            "pnl": float(pos.pnl) if pos.pnl is not None else 0.0,
            "fee": float(pos.fee) if pos.fee else 0.0,
            "close_reason": pos.close_reason,
            "opened_at": pos.opened_at.isoformat() + "Z",
            "closed_at": pos.closed_at.isoformat() + "Z" if pos.closed_at else None
        })
    return {
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
