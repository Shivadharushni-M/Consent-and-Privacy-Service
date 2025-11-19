from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any

class CreateConsentRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    purpose: str = Field(..., min_length=1, max_length=50)
    region: str = Field(..., min_length=2, max_length=50)
    policy_snapshot: Optional[Dict[str, Any]] = None

class ConsentResponse(BaseModel):
    id: int
    user_id: int
    purpose: str
    status: str
    region: str
    timestamp: datetime
    policy_snapshot: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True

