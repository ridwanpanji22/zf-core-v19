from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class DemoWallet(Base):
    __tablename__ = "demo_wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    balance: Mapped[float] = mapped_column(Numeric(20, 2), default=10000.00, nullable=False)
    initial_balance: Mapped[float] = mapped_column(Numeric(20, 2), default=10000.00, nullable=False)
    total_pnl: Mapped[float] = mapped_column(Numeric(20, 2), default=0.00, nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    win_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class DemoPosition(Base):
    __tablename__ = "demo_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False) # long | short
    size_usdt: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    leverage: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    exit_price: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    margin: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    pnl: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fee: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True) # open | closed
    close_reason: Mapped[str | None] = mapped_column(String(20), nullable=True) # manual | take_profit | stop_loss | liquidation
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
