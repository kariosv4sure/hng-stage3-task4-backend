from sqlalchemy import Column, String, Float, Integer, DateTime, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.sql import func

from app.database import Base
from app.utils.uuid7 import generate_uuid7


class ProfileModel(Base):
    __tablename__ = "profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid7)

    name = Column(String(255), nullable=False, index=True)
    gender = Column(String(6), nullable=False, index=True)
    gender_probability = Column(Float, nullable=False)

    age = Column(Integer, nullable=False, index=True)
    age_group = Column(String(20), nullable=False, index=True)

    country_id = Column(String(2), nullable=False, index=True)
    country_name = Column(String(100), nullable=False)
    country_probability = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("name", name="uq_profile_name"),
        Index("idx_gender_age", "gender", "age"),
        Index("idx_country", "country_id"),
        Index("idx_age_group", "age_group"),

        CheckConstraint("gender IN ('male', 'female')", name="ck_gender_valid"),
        CheckConstraint("gender_probability >= 0 AND gender_probability <= 1", name="ck_gender_prob_range"),
        CheckConstraint("country_probability >= 0 AND country_probability <= 1", name="ck_country_prob_range"),
        CheckConstraint("age >= 0", name="ck_age_positive"),
    )
