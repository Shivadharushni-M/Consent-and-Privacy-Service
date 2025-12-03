from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.consent import ConsentResponse, CreateConsentRequest
from app.services import consent_service
from app.utils.errors import handle_service_error
from app.utils.security import api_key_auth

router = APIRouter(prefix="/consent", tags=["consent"], dependencies=[Depends(api_key_auth)])


def _handle_consent(action, request: CreateConsentRequest, db: Session):
    try:
        return action(db=db, user_id=request.user_id, purpose=request.purpose, region=request.region, expires_at=request.get_expires_at())
    except ValueError as exc:
        handle_service_error(exc)


@router.post("/grant", response_model=ConsentResponse, status_code=201)
def grant_consent(request: CreateConsentRequest, db: Session = Depends(get_db)):
    return _handle_consent(consent_service.grant_consent, request, db)


@router.post("/revoke", response_model=ConsentResponse, status_code=201)
def revoke_consent(request: CreateConsentRequest, db: Session = Depends(get_db)):
    return _handle_consent(consent_service.revoke_consent, request, db)
