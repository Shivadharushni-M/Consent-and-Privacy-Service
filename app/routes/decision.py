from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.consent import PurposeEnum, VendorEnum
from app.schemas.decision import DecisionResponse
from app.services.decision_service import decide
from app.services.region_service import detect_region_from_ip
from app.utils.helpers import extract_client_ip
from app.utils.security import api_key_auth

router = APIRouter(tags=["decision"], dependencies=[Depends(api_key_auth)])


@router.get("/decision", response_model=DecisionResponse)
def get_decision(
    request: Request,
    user_id: UUID = Query(...),
    purpose: PurposeEnum = Query(...),
    vendor: VendorEnum = Query(default=None),
    db: Session = Depends(get_db),
) -> DecisionResponse:
    fallback_region = detect_region_from_ip(extract_client_ip(request))
    try:
        return decide(
            db, user_id, purpose, fallback_region=fallback_region, vendor=vendor
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

