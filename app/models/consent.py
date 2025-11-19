from sqlalchemy import Column, Integer, String, DateTime, JSON, Index
from sqlalchemy.sql import func
from app.db.database import Base

class ConsentHistory(Base):
    __tablename__ = "consent_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    purpose = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    region = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    policy_snapshot = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index('idx_user_purpose', 'user_id', 'purpose'),
    )

