from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import cast, String
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.audit import AuditLog
from app.models.consent import PurposeEnum, RegionEnum, RequestTypeEnum, SubjectRequest
from app.models.policy import Policy, PolicyVersion
from app.schemas.consent import AuditLogResponse
from app.schemas.policy import PolicyVersionResponse
from app.utils.security import api_key_auth

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin-v1"],
    dependencies=[Depends(api_key_auth)],
)


