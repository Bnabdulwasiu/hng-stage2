from sqlalchemy import Column, String, Float, Integer, DateTime
import uuid6
from datetime import datetime, timezone
from database import Base
from sqlalchemy.dialects.postgresql import UUID

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    name = Column(String, unique=True, index=False)
    gender = Column(String, nullable=False)
    gender_probability = Column(Float, nullable=False)
    age = Column(Integer, nullable=False)
    age_group = Column(String, nullable=False)
    country_id = Column(String(2), nullable=False)
    country_name = Column(String, nullable=False)
    country_probability = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
