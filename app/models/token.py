from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.sql import func
from app.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True)

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    token_hash = Column(String(255), unique=True, nullable=False)

    expires_at = Column(DateTime(timezone=True), nullable=False)

    is_revoked = Column(Boolean, default=False, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


Index("idx_refresh_user_active", RefreshToken.user_id, RefreshToken.is_revoked)

