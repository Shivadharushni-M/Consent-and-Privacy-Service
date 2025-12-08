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
from app.utils.security import AuthenticatedActor, get_current_actor, validate_user_action

router = APIRouter(tags=["decision"])


@router.get(
    "/decision",
    response_model=DecisionResponse,
    description="Get consent decision for a user and purpose. User JWT token required - users can only check decisions for themselves."
)
def get_decision(request: Request, user_id: UUID = Query(...), purpose: PurposeEnum = Query(...), db: Session = Depends(get_db), actor: AuthenticatedActor = Depends(get_current_actor)):
    try:
        validate_user_action(actor, user_id)
        return decide(db, user_id, purpose, fallback_region=detect_region_from_ip(extract_client_ip(request)), actor=actor)
    except ValueError as exc:
        handle_service_error(exc)
