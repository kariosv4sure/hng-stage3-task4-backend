import enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, Index
from sqlalchemy.sql import func
from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    github_id = Column(String(50), unique=True, nullable=False, index=True)
    github_username = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=True)

    role = Column(SQLEnum(UserRole), default=UserRole.ANALYST, nullable=False, index=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

