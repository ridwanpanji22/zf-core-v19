from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, LargeBinary, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class UserApiKey(Base):
    __tablename__ = "user_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    api_key_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    secret_key_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    passphrase_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    api_key_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    permission_level: Mapped[str | None] = mapped_column(String(20), nullable=True) # read_only | trade | withdraw
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
