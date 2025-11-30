from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.decision_v1 import DecisionRequest, DecisionResponse
from app.services.decision_v1_service import evaluate_decision
from app.utils.helpers import extract_client_ip
from app.utils.security import api_key_auth

router = APIRouter(
    prefix="/api/v1/decisions",
    tags=["decisions"],
    dependencies=[Depends(api_key_auth)],
)


@router.post("", response_model=DecisionResponse)
def create_decision(
    request: DecisionRequest,
    http_request: Request,
    db: Session = Depends(get_db),
) -> DecisionResponse:
    try:
        # Auto-detect region if not provided
        region_code = request.region_code
        if not region_code:
            client_ip = extract_client_ip(http_request)
            from app.services.region_service import detect_region_from_ip
            region_code = detect_region_from_ip(client_ip).value
        
        result = evaluate_decision(
            db=db,
            subject_external_id=request.subject_external_id,
            subject_id=request.subject_id,
            purpose_code=request.purpose_code,
            vendor_code=request.vendor_code,
            region_code=region_code,
            timestamp=request.timestamp or datetime.utcnow(),
            tenant_id=request.tenant_id,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
