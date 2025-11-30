from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.events import EventIn, EventResponse
from app.services import event_service
from app.utils.helpers import extract_client_ip
from app.utils.security import api_key_auth

router = APIRouter(tags=["events"], dependencies=[Depends(api_key_auth)])


@router.post("/events", response_model=EventResponse)
def intake_event(event: EventIn, request: Request, db: Session = Depends(get_db)) -> EventResponse:
    client_ip = extract_client_ip(request)
    try:
        return event_service.process_event(db, event, client_ip)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

