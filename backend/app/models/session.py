from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CodeRedTracker(Base):
    __tablename__ = "code_red_tracker"

    symbol: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("asset_registry.symbol", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    consecutive_sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SessionJournal(Base):
    __tablename__ = "session_journals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    avg_zf_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    code_red_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alerts_sent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    errors_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    omega_changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class SystemEvent(Base):
    __tablename__ = "system_events"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('circuit_breaker', 'mode_dingin', 'black_swan', 'deploy', 'admin_action')",
            name="ck_system_events_event_type",
        ),
        CheckConstraint(
            "severity IN ('critical', 'warning', 'info')",
            name="ck_system_events_severity",
        ),
    )
