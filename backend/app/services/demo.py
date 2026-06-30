import json
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.asset import AssetRegistry
from app.models.demo import DemoPosition, DemoWallet

logger = structlog.get_logger()
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_or_create_wallet(db: AsyncSession, user_id: int) -> DemoWallet:
    """Get active demo wallet for user, auto-create if not exists."""
    res = await db.execute(select(DemoWallet).where(DemoWallet.user_id == user_id))
    wallet = res.scalar_one_or_none()
    if not wallet:
        initial = Decimal(str(settings.DEMO_INITIAL_BALANCE))
        wallet = DemoWallet(
            user_id=user_id,
            balance=initial,
            initial_balance=initial,
            total_pnl=Decimal("0.0"),
            total_trades=0,
            win_trades=0
        )
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
        logger.info("Demo wallet auto-created", user_id=user_id, balance=initial)
    return wallet

async def reset_wallet(db: AsyncSession, user_id: int) -> DemoWallet:
    """Close all open virtual positions, reset wallet balance and stats."""
    wallet = await get_or_create_wallet(db, user_id)

    pos_res = await db.execute(
        select(DemoPosition)
        .where(DemoPosition.user_id == user_id)
        .where(DemoPosition.status == "open")
    )
    open_positions = pos_res.scalars().all()
    for pos in open_positions:
        await close_position(db, user_id, pos.id, reason="manual")

    initial = Decimal(str(settings.DEMO_INITIAL_BALANCE))
    wallet.balance = initial
    wallet.total_pnl = Decimal("0.0")
    wallet.total_trades = 0
    wallet.win_trades = 0
    wallet.last_reset_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(wallet)
    logger.info("Demo wallet reset complete", user_id=user_id)
    return wallet

async def open_position(
    db: AsyncSession,
    user_id: int,
    symbol: str,
    side: str,
    size_usdt: float,
    leverage: int
) -> DemoPosition:
    """Open a virtual position if margin is available."""
    max_lev = settings.DEMO_MAX_LEVERAGE
    if leverage < 1 or leverage > max_lev:
        raise ValueError(f"Leverage must be between 1 and {max_lev}")

    if size_usdt <= 0:
        raise ValueError("Order size must be greater than 0")

    reg_res = await db.execute(select(AssetRegistry).where(AssetRegistry.symbol == symbol))
    asset = reg_res.scalar_one_or_none()
    if not asset:
        # ponytail: fallback to bootstrap symbols when registry is empty (pre-00:30 UTC seed)
        if symbol not in settings.BOOTSTRAP_SYMBOLS:
            raise ValueError("Asset is inactive or not registered")
    elif not asset.is_active:
        raise ValueError("Asset is inactive or not registered")

    val = await redis_client.get(f"metrics:{symbol}")
    if not val:
        raise ValueError(f"No real-time market data available for {symbol}")

    metrics = json.loads(val)
    price = Decimal(str(metrics["price"]))

    wallet = await get_or_create_wallet(db, user_id)
    margin = Decimal(str(size_usdt)) / Decimal(str(leverage))
    fee = Decimal(str(size_usdt)) * Decimal("0.0005") # 0.05% taker fee

    if wallet.balance < (margin + fee):
        raise ValueError("Insufficient demo balance to cover margin and fee")

    wallet.balance -= (margin + fee)

    pos = DemoPosition(
        user_id=user_id,
        symbol=symbol,
        side=side.lower(),
        size_usdt=Decimal(str(size_usdt)),
        leverage=leverage,
        entry_price=price,
        margin=margin,
        fee=fee,
        status="open",
        opened_at=datetime.now(timezone.utc)
    )
    db.add(pos)
    await db.commit()
    await db.refresh(pos)

    logger.info("Demo position opened", user_id=user_id, symbol=symbol, side=side, size=size_usdt)
    return pos

async def close_position(db: AsyncSession, user_id: int, position_id: int, reason: str = "manual") -> DemoPosition:
    """Close an open virtual position at current price and update wallet stats."""
    res = await db.execute(
        select(DemoPosition)
        .where(DemoPosition.id == position_id)
        .where(DemoPosition.user_id == user_id)
        .where(DemoPosition.status == "open")
    )
    pos = res.scalar_one_or_none()
    if not pos:
        raise ValueError("Position not found or already closed")

    val = await redis_client.get(f"metrics:{pos.symbol}")
    price = pos.entry_price # fallback
    if val:
        try:
            price = Decimal(str(json.loads(val)["price"]))
        except Exception:
            pass

    # PnL = ((exit - entry) / entry) * size * leverage
    # Leverage multiplier is CRITICAL — without it, 10x position PnL = 1x position PnL
    entry = Decimal(str(pos.entry_price))
    size = Decimal(str(pos.size_usdt))
    leverage = Decimal(str(pos.leverage))

    if pos.side == "long":
        pnl = ((price - entry) / entry) * size * leverage
    else:
        pnl = ((entry - price) / entry) * size * leverage

    close_fee = size * Decimal("0.0005")

    pos.exit_price = price
    pos.pnl = pnl
    pos.fee += close_fee
    pos.status = "closed"
    pos.close_reason = reason
    pos.closed_at = datetime.now(timezone.utc)

    wallet = await get_or_create_wallet(db, user_id)
    return_amount = pos.margin + pnl - close_fee

    wallet.balance += return_amount
    wallet.total_pnl += pnl
    wallet.total_trades += 1
    if pnl > 0:
        wallet.win_trades += 1

    await db.commit()
    await db.refresh(pos)
    logger.info("Demo position closed", id=position_id, symbol=pos.symbol, pnl=pnl, return_amount=return_amount)
    return pos

async def check_liquidations(db: AsyncSession):
    """Check all open virtual positions and liquidate if loss exceeds margin."""
    res = await db.execute(select(DemoPosition).where(DemoPosition.status == "open"))
    positions = res.scalars().all()

    for pos in positions:
        val = await redis_client.get(f"metrics:{pos.symbol}")
        if not val:
            continue
        try:
            price = Decimal(str(json.loads(val)["price"]))
        except Exception:
            continue

        entry = Decimal(str(pos.entry_price))
        size = Decimal(str(pos.size_usdt))
        leverage = Decimal(str(pos.leverage))

        if pos.side == "long":
            unrealized_pnl = ((price - entry) / entry) * size * leverage
        else:
            unrealized_pnl = ((entry - price) / entry) * size * leverage

        # Liquidation: loss >= margin
        if -unrealized_pnl >= pos.margin:
            logger.info("Liquidating demo position", id=pos.id, symbol=pos.symbol, pnl=unrealized_pnl)
            try:
                await close_position(db, pos.user_id, pos.id, reason="liquidation")
            except Exception as e:
                logger.error("Failed to liquidate position", id=pos.id, error=str(e))
