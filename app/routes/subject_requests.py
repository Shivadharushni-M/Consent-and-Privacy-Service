from datetime import timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.consent import RequestStatusEnum, RequestTypeEnum, SubjectRequest
from app.models.tokens import TokenPurposeEnum, VerificationToken
from app.schemas.subject_requests import DataAccessResponse, DataExportResponse, SubjectRequestIn, SubjectRequestOut, VerifyTokenRequest
from app.services import subject_request_service
from app.utils.errors import handle_service_error
from app.utils.helpers import get_utc_now
from app.utils.security import api_key_auth, generate_verification_token, verify_token

router = APIRouter(prefix="/subject-requests", tags=["subject-requests"], dependencies=[Depends(api_key_auth)])


def _get_request(request_id: UUID, db: Session) -> SubjectRequest:
    request = db.get(SubjectRequest, request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request_not_found")
    return request


def _verify_token(token: str, request: SubjectRequest, expected_type: RequestTypeEnum) -> None:
    data = verify_token(token)
    if not data or str(request.user_id) != data.get("user_id"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_verification_token")
    if data.get("request_type") != expected_type.value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Token is for '{data.get('request_type')}' request, but endpoint requires '{expected_type.value}'")


@router.post("", response_model=SubjectRequestOut, status_code=status.HTTP_201_CREATED)
def create_subject_request(payload: SubjectRequestIn, db: Session = Depends(get_db)):
    try:
        if payload.request_type == RequestTypeEnum.RECTIFY:
            request = subject_request_service.process_rectify_request(db, payload.user_id, new_email=payload.new_email, new_region=payload.new_region)
            return SubjectRequestOut(request_id=request.id, status=request.status, request_type=request.request_type, verification_token=None)
        request = subject_request_service.create_request(db, payload.user_id, payload.request_type)
        token = generate_verification_token({"user_id": str(request.user_id), "request_type": payload.request_type.value})
        purpose_map = {RequestTypeEnum.EXPORT: TokenPurposeEnum.RIGHTS_EXPORT, RequestTypeEnum.DELETE: TokenPurposeEnum.RIGHTS_DELETION, RequestTypeEnum.ACCESS: TokenPurposeEnum.RIGHTS_ACCESS}
        token_record = VerificationToken(token=token, purpose=purpose_map[payload.request_type].value, subject_id=request.user_id, tenant_id=request.tenant_id, expires_at=get_utc_now() + timedelta(days=7))
        db.add(token_record)
        db.flush()
        request.verification_token_id = token_record.id
        db.commit()
        db.refresh(request)
        return SubjectRequestOut(request_id=request.id, status=request.status, request_type=request.request_type, verification_token=token)
    except ValueError as exc:
        handle_service_error(exc)


@router.get("/export/{request_id}", response_model=DataExportResponse)
def get_export(request_id: UUID, token: str = Query(...), db: Session = Depends(get_db)):
    request = _get_request(request_id, db)
    if request.request_type != RequestTypeEnum.EXPORT:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Request type is '{request.request_type.value}'. Use /subject-requests/access/{request_id} for access requests")
    _verify_token(token, request, RequestTypeEnum.EXPORT)
    if request.status != RequestStatusEnum.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="request_not_completed")
    return subject_request_service.process_export_request(db, request)


@router.get("/access/{request_id}", response_model=DataAccessResponse)
def get_access(request_id: UUID, token: str = Query(...), db: Session = Depends(get_db)):
    request = _get_request(request_id, db)
    if request.request_type != RequestTypeEnum.ACCESS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Request type is '{request.request_type.value}', use /export endpoint for export requests")
    _verify_token(token, request, RequestTypeEnum.ACCESS)
    return subject_request_service.process_access_request(db, request)


@router.post("/verify", status_code=status.HTTP_200_OK)
def verify_token_endpoint(payload: VerifyTokenRequest, db: Session = Depends(get_db)):
    request = _get_request(payload.request_id, db)
    try:
        _verify_token(payload.token, request, request.request_type)
        return {"valid": True, "request_id": str(payload.request_id), "request_type": request.request_type.value, "status": request.status.value}
    except HTTPException:
        return {"valid": False, "request_id": str(payload.request_id), "error": "invalid_verification_token"}
