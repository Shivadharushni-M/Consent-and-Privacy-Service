from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.consent import RegionEnum, User
from app.services.region_service import detect_region_from_ip
from app.utils.helpers import get_utc_now
from app.services.user_service import validate_email


def get_or_create_subject(
    db: Session,
    *,
    external_id: Optional[str] = None,
    identifier_type: Optional[str] = None,
    identifier_value: Optional[str] = None,
    region_code: Optional[RegionEnum] = None,
    tenant_id: Optional[str] = None,
) -> User:
    # Check email FIRST since it has a unique constraint
    # This prevents IntegrityError when email already exists
    # Check both explicit email type and if identifier_value looks like an email
    email_to_check = None
    if identifier_type == "email" and identifier_value:
        email_to_check = identifier_value
    elif identifier_value and "@" in identifier_value and "." in identifier_value.split("@")[-1]:
        # identifier_value looks like an email even if type isn't specified
        email_to_check = identifier_value
    
    if email_to_check:
        user = db.query(User).filter(
            User.email == email_to_check,
            User.deleted_at.is_(None)
        ).first()
        if user:
            # Update region if provided
            if region_code and user.region != region_code:
                user.region = region_code
                db.add(user)
                db.commit()
                db.refresh(user)
            return user
    
    # Try to find by external_id + tenant_id
    if external_id and tenant_id:
        user = db.query(User).filter(
            User.external_id == external_id,
            User.tenant_id == tenant_id,
            User.deleted_at.is_(None)
        ).first()
        if user:
            # Update region if provided
            if region_code and user.region != region_code:
                user.region = region_code
                db.add(user)
                db.commit()
                db.refresh(user)
            return user
    
    # Try to find by external_id alone (if no tenant_id provided)
    if external_id and not tenant_id:
        user = db.query(User).filter(
            User.external_id == external_id,
            User.tenant_id.is_(None),
            User.deleted_at.is_(None)
        ).first()
        if user:
            # Update region if provided
            if region_code and user.region != region_code:
                user.region = region_code
                db.add(user)
                db.commit()
                db.refresh(user)
            return user
    
    # Create new subject
    import uuid
    # Use detected email if we found one, otherwise use identifier_value if it's an email, otherwise generate placeholder
    if email_to_check:
        email = email_to_check
    elif identifier_type == "email" and identifier_value:
        email = identifier_value
    else:
        email = f"user_{external_id or uuid.uuid4().hex[:8]}@placeholder.com"
    region = region_code or RegionEnum.ROW
    
    # Check if the generated email already exists (for placeholder emails)
    # This prevents IntegrityError for generated emails
    # We check this BEFORE creating to catch conflicts early
    if identifier_type != "email":
        # Check for any user with this email (including soft-deleted)
        existing_user = db.query(User).filter(
            User.email == email
        ).first()
        if existing_user:
            if existing_user.deleted_at is None:
                # Active user exists, return it
                # Update region if provided
                if region_code and existing_user.region != region_code:
                    existing_user.region = region_code
                    db.add(existing_user)
                    db.commit()
                    db.refresh(existing_user)
                return existing_user
            else:
                # Soft-deleted user exists, restore it
                existing_user.deleted_at = None
                if external_id:
                    existing_user.external_id = external_id
                if tenant_id:
                    existing_user.tenant_id = tenant_id
                if identifier_type:
                    existing_user.primary_identifier_type = identifier_type
                if identifier_value:
                    existing_user.primary_identifier_value = identifier_value
                if region_code:
                    existing_user.region = region_code
                db.add(existing_user)
                db.commit()
                db.refresh(existing_user)
                return existing_user
    
    user = User(
        external_id=external_id,
        tenant_id=tenant_id,
        email=email,
        primary_identifier_type=identifier_type,
        primary_identifier_value=identifier_value,
        region=region
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as exc:
        db.rollback()
        # Refresh the session to ensure we can query after rollback
        db.expire_all()
        
        # Try to find the existing user by email (for both real and placeholder emails)
        # Check both active and soft-deleted users since unique constraint applies to all
        existing_user = db.query(User).filter(
            User.email == email
        ).first()
        if existing_user and existing_user.deleted_at is None:
            # Return existing active user instead of raising error
            # This makes the endpoint idempotent
            # Update region if provided
            if region_code and existing_user.region != region_code:
                existing_user.region = region_code
                db.add(existing_user)
                db.commit()
                db.refresh(existing_user)
            return existing_user
        
        # If we can't find by email, try to find by external_id as last resort
        if external_id:
            existing_user = db.query(User).filter(
                User.external_id == external_id,
                User.deleted_at.is_(None)
            ).first()
            if existing_user:
                # Update region if provided
                if region_code and existing_user.region != region_code:
                    existing_user.region = region_code
                    db.add(existing_user)
                    db.commit()
                    db.refresh(existing_user)
                return existing_user
        
        # If we still can't find it, there might be a soft-deleted user with this email
        # In that case, we should restore it or provide a better error message
        soft_deleted = db.query(User).filter(
            User.email == email,
            User.deleted_at.isnot(None)
        ).first()
        if soft_deleted:
            # Restore the soft-deleted user
            soft_deleted.deleted_at = None
            if external_id:
                soft_deleted.external_id = external_id
            if tenant_id:
                soft_deleted.tenant_id = tenant_id
            if identifier_type:
                soft_deleted.primary_identifier_type = identifier_type
            if identifier_value:
                soft_deleted.primary_identifier_value = identifier_value
            if region_code:
                soft_deleted.region = region_code
            db.add(soft_deleted)
            db.commit()
            db.refresh(soft_deleted)
            return soft_deleted
        
        raise ValueError("duplicate_subject") from exc


def get_subject_by_external_id(db: Session, external_id: str, tenant_id: Optional[str] = None) -> User:
    query = db.query(User).filter(
        User.external_id == external_id,
        User.deleted_at.is_(None)
    )
    if tenant_id:
        query = query.filter(User.tenant_id == tenant_id)
    user = query.first()
    if not user:
        raise ValueError("subject_not_found")
    return user


def update_subject(
    db: Session,
    subject_id: UUID,
    *,
    identifier_type: Optional[str] = None,
    identifier_value: Optional[str] = None,
) -> User:
    user = db.get(User, subject_id)
    if not user or user.deleted_at:
        raise ValueError("subject_not_found")
    
    # Region is auto-detected and cannot be manually updated
    if identifier_type:
        user.primary_identifier_type = identifier_type
    if identifier_value:
        if identifier_type == "email":
            user.email = validate_email(identifier_value)
        user.primary_identifier_value = identifier_value
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_subject(db: Session, subject_id: UUID) -> None:
    user = db.get(User, subject_id)
    if not user:
        raise ValueError("subject_not_found")
    
    user.deleted_at = get_utc_now()
    db.add(user)
    db.commit()
