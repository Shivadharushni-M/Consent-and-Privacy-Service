from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.consent import PurposeEnum
from app.schemas.decision import DecisionResponse
from app.services.decision_service import decide
from app.services.region_service import detect_region_from_ip
from app.utils.errors import handle_service_error
from app.utils.helpers import extract_client_ip
from app.utils.security import api_key_auth

router = APIRouter(tags=["decision"], dependencies=[Depends(api_key_auth)])


@router.get("/decision", response_model=DecisionResponse)
def get_decision(request: Request, user_id: UUID = Query(...), purpose: PurposeEnum = Query(...), db: Session = Depends(get_db)):
    try:
        return decide(db, user_id, purpose, fallback_region=detect_region_from_ip(extract_client_ip(request)))
    except ValueError as exc:
        handle_service_error(exc)
