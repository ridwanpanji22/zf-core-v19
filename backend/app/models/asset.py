from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AssetRegistry(Base):
    __tablename__ = "asset_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    base_currency: Mapped[str] = mapped_column(String(20), nullable=False)
    inst_type: Mapped[str] = mapped_column(String(10), default="SWAP", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dampening_factor: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    dampening_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AssetSnapshot(Base):
    __tablename__ = "asset_snapshots"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    symbol: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("asset_registry.symbol", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    zf_score: Mapped[float] = mapped_column(Float, nullable=False)
    psi_total: Mapped[float] = mapped_column(Float, nullable=False)
    d_res: Mapped[float] = mapped_column(Float, nullable=False)
    oi: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    funding_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_24h: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    bid_depth_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    ofi: Mapped[float | None] = mapped_column(Float, nullable=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    predicted_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        CheckConstraint("mode IN ('heartbeat', 'deep_analysis')", name="ck_asset_snapshots_mode"),
        CheckConstraint("status IN ('normal', 'waspada', 'code_red')", name="ck_asset_snapshots_status"),
        Index("ix_asset_snapshots_symbol_time", "symbol", "time"),
    )


class TickData(Base):
    """Raw tick data — retention 30 days (purge via Celery beat task)."""
    __tablename__ = "tick_data"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    symbol: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("asset_registry.symbol", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    last_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    best_bid: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    best_ask: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)

    __table_args__ = (
        Index("ix_tick_data_symbol_time", "symbol", "time"),
    )
