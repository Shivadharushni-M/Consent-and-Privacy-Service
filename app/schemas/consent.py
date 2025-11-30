from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, Union
import uuid

class CreateConsentRequest(BaseModel):
    user_id: Union[int, str] = Field(..., description="User ID (integer or UUID string)")
    purpose: str = Field(..., min_length=1, max_length=50)
    region: str = Field(..., min_length=2, max_length=50)
    policy_snapshot: Optional[Dict[str, Any]] = None

class ConsentResponse(BaseModel):
    id: int
    user_id: Union[int, str, uuid.UUID]  # Can be UUID or int
    purpose: str
    status: str
    region: str
    timestamp: datetime
    policy_snapshot: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True

