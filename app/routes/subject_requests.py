from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.consent import RequestTypeEnum, SubjectRequest
from app.schemas.subject_requests import SubjectRequestIn, SubjectRequestOut
from app.services import subject_request_service

router = APIRouter(prefix="/subject-requests", tags=["subject-requests"])

_ERROR_MAP = {
    "user_not_found": (status.HTTP_404_NOT_FOUND, "user_not_found"),
    "unsupported_request_type": (status.HTTP_422_UNPROCESSABLE_ENTITY, "unsupported_request_type"),
}


def _handle_error(exc: ValueError) -> None:
    status_code, detail = _ERROR_MAP.get(
        str(exc), (status.HTTP_400_BAD_REQUEST, "invalid_request")
    )
    raise HTTPException(status_code=status_code, detail=detail) from exc


@router.post("", response_model=SubjectRequestOut, status_code=status.HTTP_201_CREATED)
def create_subject_request(payload: SubjectRequestIn, db: Session = Depends(get_db)):
    try:
        request = subject_request_service.create_request(db, payload.user_id, payload.request_type)
        return SubjectRequestOut(
            request_id=request.id,
            status=request.status,
            request_type=request.request_type,
        )
    except ValueError as exc:
        _handle_error(exc)


@router.get("/{request_id}")
def process_subject_request(request_id: UUID, db: Session = Depends(get_db)):
    request = db.get(SubjectRequest, request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request_not_found")

    if request.request_type == RequestTypeEnum.EXPORT:
        return subject_request_service.process_export_request(db, request)
    if request.request_type == RequestTypeEnum.DELETE:
        return subject_request_service.process_delete_request(db, request)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unsupported_request_type"
    )


