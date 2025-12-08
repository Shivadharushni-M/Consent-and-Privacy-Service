from datetime import timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.consent import RequestTypeEnum, SubjectRequest
from app.models.tokens import TokenPurposeEnum, VerificationToken
from app.schemas.subject_requests import DataAccessResponse, DataExportResponse, SubjectRequestIn, SubjectRequestOut, VerifyTokenRequest
from app.services import subject_request_service
from app.utils.errors import handle_service_error
from app.utils.helpers import get_utc_now
from app.utils.security import AuthenticatedActor, get_current_actor, generate_verification_token, validate_user_action, verify_token

router = APIRouter(prefix="/subject-requests", tags=["subject-requests"])

_PURPOSE_MAP = {RequestTypeEnum.EXPORT: TokenPurposeEnum.RIGHTS_EXPORT, RequestTypeEnum.DELETE: TokenPurposeEnum.RIGHTS_DELETION, RequestTypeEnum.ACCESS: TokenPurposeEnum.RIGHTS_ACCESS}


def _get_request(request_id: UUID, db: Session) -> SubjectRequest:
    request = db.get(SubjectRequest, request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request_not_found")
    return request


def _validate_request_type(request: SubjectRequest, expected: RequestTypeEnum, alt_path: str) -> None:
    if request.request_type != expected:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Request type is '{request.request_type.value}'. Use {alt_path}")


def _verify_token(token: str, request: SubjectRequest, expected_type: RequestTypeEnum) -> None:
    data = verify_token(token)
    if not data or str(request.user_id) != data.get("user_id"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_verification_token")
    if data.get("request_type") != expected_type.value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Token mismatch: token is for '{data.get('request_type')}' but endpoint requires '{expected_type.value}'. Use /subject-requests/{data.get('request_type')}/{request.id}")


@router.post(
    "",
    response_model=SubjectRequestOut,
    status_code=status.HTTP_201_CREATED,
    description="Create a subject rights request. User JWT token required - users can only create requests for themselves."
)
def create_subject_request(payload: SubjectRequestIn, db: Session = Depends(get_db), actor: AuthenticatedActor = Depends(get_current_actor)):
    try:
        validate_user_action(actor, payload.user_id)
        if payload.request_type == RequestTypeEnum.RECTIFY:
            request = subject_request_service.process_rectify_request(db, payload.user_id, new_region=payload.region, actor=actor)
            return SubjectRequestOut(request_id=request.id, status=request.status, request_type=request.request_type, verification_token=None)
        request = subject_request_service.create_request(db, payload.user_id, payload.request_type, actor=actor)
        token = generate_verification_token({"user_id": str(request.user_id), "request_type": payload.request_type.value})
        token_record = VerificationToken(token=token, purpose=_PURPOSE_MAP[payload.request_type].value, subject_id=request.user_id, tenant_id=request.tenant_id, expires_at=get_utc_now() + timedelta(days=7))
        db.add(token_record)
        db.flush()
        request.verification_token_id = token_record.id
        db.commit()
        db.refresh(request)
        return SubjectRequestOut(request_id=request.id, status=request.status, request_type=request.request_type, verification_token=token)
    except ValueError as exc:
        handle_service_error(exc)


@router.get(
    "/export/{request_id}",
    response_model=DataExportResponse,
    description="Get export data for a completed request. User JWT token required - users can only access their own export data."
)
def get_export(request_id: UUID, token: str = Query(...), db: Session = Depends(get_db), actor: AuthenticatedActor = Depends(get_current_actor)):
    request = _get_request(request_id, db)
    validate_user_action(actor, request.user_id)
    _validate_request_type(request, RequestTypeEnum.EXPORT, f"/subject-requests/access/{request_id} for access requests")
    _verify_token(token, request, RequestTypeEnum.EXPORT)
    return subject_request_service.process_export_request(db, request, actor=actor)


@router.get(
    "/access/{request_id}",
    response_model=DataAccessResponse,
    description="Get access data for a request. User JWT token required - users can only access their own data."
)
def get_access(request_id: UUID, token: str = Query(...), db: Session = Depends(get_db), actor: AuthenticatedActor = Depends(get_current_actor)):
    request = _get_request(request_id, db)
    validate_user_action(actor, request.user_id)
    _validate_request_type(request, RequestTypeEnum.ACCESS, "/export endpoint for export requests")
    _verify_token(token, request, RequestTypeEnum.ACCESS)
    return subject_request_service.process_access_request(db, request, actor=actor)


@router.delete(
    "/delete/{request_id}",
    description="Process deletion request. User JWT token required - users can only delete their own data."
)
def delete_data(request_id: UUID, token: str = Query(...), db: Session = Depends(get_db), actor: AuthenticatedActor = Depends(get_current_actor)):
    request = _get_request(request_id, db)
    validate_user_action(actor, request.user_id)
    _validate_request_type(request, RequestTypeEnum.DELETE, f"/subject-requests/delete/{request_id} for delete requests")
    _verify_token(token, request, RequestTypeEnum.DELETE)
    try:
        return subject_request_service.process_delete_request(db, request)
    except ValueError as exc:
        handle_service_error(exc)


@router.post(
    "/verify",
    status_code=status.HTTP_200_OK,
    description="Verify a request token. User JWT token required - users can only verify tokens for their own requests. Sets status to VERIFIED if token is valid."
)
def verify_token_endpoint(payload: VerifyTokenRequest, db: Session = Depends(get_db), actor: AuthenticatedActor = Depends(get_current_actor)):
    from app.models.consent import RequestStatusEnum
    request = _get_request(payload.request_id, db)
    validate_user_action(actor, request.user_id)
    try:
        _verify_token(payload.token, request, request.request_type)
        if request.status == RequestStatusEnum.PENDING_VERIFICATION:
            request.status = RequestStatusEnum.VERIFIED
            db.commit()
            db.refresh(request)
        return {"valid": True, "request_id": str(payload.request_id), "request_type": request.request_type.value, "status": request.status.value}
    except HTTPException:
        return {"valid": False, "request_id": str(payload.request_id), "error": "invalid_verification_token"}
