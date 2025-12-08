from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.consent import ConsentResponse, CreateConsentRequest
from app.services import consent_service
from app.utils.errors import handle_service_error
from app.utils.security import AuthenticatedActor, get_current_actor, security_scheme, validate_user_action

router = APIRouter(prefix="/consent", tags=["consent"])


def _handle_consent(action, request: CreateConsentRequest, db: Session, actor: AuthenticatedActor):
    try:
        validate_user_action(actor, request.user_id)
        return action(db=db, user_id=request.user_id, purpose=request.purpose, region=request.region, expires_at=request.get_expires_at(), actor=actor)
    except ValueError as exc:
        handle_service_error(exc)


@router.post("/grant", response_model=ConsentResponse, status_code=201, description="Grant consent for a purpose. User JWT token required - users can only grant consent for themselves.", dependencies=[Depends(security_scheme)])
def grant_consent(request: CreateConsentRequest, db: Session = Depends(get_db), actor: AuthenticatedActor = Depends(get_current_actor)):
    return _handle_consent(consent_service.grant_consent, request, db, actor)


@router.post("/revoke", response_model=ConsentResponse, status_code=201, description="Revoke consent for a purpose. User JWT token required - users can only revoke consent for themselves.", dependencies=[Depends(security_scheme)])
def revoke_consent(request: CreateConsentRequest, db: Session = Depends(get_db), actor: AuthenticatedActor = Depends(get_current_actor)):
    return _handle_consent(consent_service.revoke_consent, request, db, actor)
