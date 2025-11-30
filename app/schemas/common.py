from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Union

class UserCreateRequest(BaseModel):
    user_id: Optional[Union[int, str]] = Field(None, description="User ID")
    email: Optional[str] = Field(None, description="User email")
    name: Optional[str] = Field(None, description="User name")
    metadata: Optional[Dict[str, Any]] = None

class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class EventRequest(BaseModel):
    event_type: str = Field(..., description="Type of event")
    user_id: Optional[Union[int, str]] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

class SubjectRequestCreate(BaseModel):
    subject_id: Union[int, str] = Field(..., description="Subject ID")
    request_type: str = Field(..., description="Type of request (export, delete, access)")
    metadata: Optional[Dict[str, Any]] = None

class VendorConsentRequest(BaseModel):
    user_id: Union[int, str] = Field(..., description="User ID")
    vendor_id: str = Field(..., description="Vendor ID")
    purpose: Optional[str] = None
    region: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class PreferencesUpdateRequest(BaseModel):
    user_id: Union[int, str] = Field(..., description="User ID")
    preferences: Dict[str, Any] = Field(
        ..., 
        description="User preferences - can include: communication preferences (email, sms, push), privacy settings, consent preferences, language, notifications, etc.",
        example={
            "communication": {
                "email": True,
                "sms": False,
                "push": True
            },
            "privacy": {
                "data_sharing": False,
                "analytics": True,
                "marketing": False
            },
            "consent": {
                "analytics": True,
                "advertising": False,
                "functional": True
            },
            "language": "en",
            "notifications": {
                "consent_updates": True,
                "policy_changes": True,
                "security_alerts": True
            }
        }
    )
    metadata: Optional[Dict[str, Any]] = None
