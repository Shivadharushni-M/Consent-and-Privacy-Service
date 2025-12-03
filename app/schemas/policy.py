from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel


class PolicySnapshotResponse(BaseModel):
    snapshot: Dict[str, Any]
    region: Optional[str] = None
    tenant_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    source: str
