from fastapi import APIRouter, Depends, HTTPException
from app.utils.security import api_key_auth
from app.schemas.common import EventRequest

router = APIRouter(prefix="/events", tags=["events"], dependencies=[Depends(api_key_auth)])

@router.post("", status_code=201)
def intake_event(event: EventRequest):
    """Intake Event"""
    try:
        return {
            "message": "Event received",
            "event_type": event.event_type,
            "user_id": event.user_id,
            "data": event.data,
            "timestamp": event.timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
