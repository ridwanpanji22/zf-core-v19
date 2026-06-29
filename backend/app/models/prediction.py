from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PredictionLog(Base):
    __tablename__ = "prediction_log"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), primary_key=True, nullable=False)
    prediction_type: Mapped[str] = mapped_column(String(30), nullable=False) # decay_10d | zf_score_change
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[float | None] = mapped_column(Float, nullable=True)
    omega_w1: Mapped[float] = mapped_column(Float, nullable=False)
    omega_w2: Mapped[float] = mapped_column(Float, nullable=False)
    omega_w3: Mapped[float] = mapped_column(Float, nullable=False)

class CalibrationLog(Base):
    __tablename__ = "calibration_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    calibrated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    omega_w1_old: Mapped[float] = mapped_column(Float, nullable=False)
    omega_w2_old: Mapped[float] = mapped_column(Float, nullable=False)
    omega_w3_old: Mapped[float] = mapped_column(Float, nullable=False)
    omega_w1_new: Mapped[float] = mapped_column(Float, nullable=False)
    omega_w2_new: Mapped[float] = mapped_column(Float, nullable=False)
    omega_w3_new: Mapped[float] = mapped_column(Float, nullable=False)
    avg_error_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_error_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    samples_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
