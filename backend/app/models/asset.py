from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Float, DateTime, Numeric
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
    symbol: Mapped[str] = mapped_column(String(50), primary_key=True, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    zf_score: Mapped[float] = mapped_column(Float, nullable=False)
    psi_total: Mapped[float] = mapped_column(Float, nullable=False)
    d_res: Mapped[float] = mapped_column(Float, nullable=False)
    oi: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    funding_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_24h: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    bid_depth_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    ofi: Mapped[float | None] = mapped_column(Float, nullable=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False) # heartbeat | deep_analysis
    status: Mapped[str] = mapped_column(String(20), nullable=False) # normal | waspada | code_red
    predicted_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
