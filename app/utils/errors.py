from fastapi import HTTPException, status

_ERROR_MAP: dict[str, tuple[int, str]] = {
    "user_not_found": (status.HTTP_404_NOT_FOUND, "User not found"),
    "invalid_email": (status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid email"),
    "invalid_region": (status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid region"),
    "duplicate_email": (status.HTTP_409_CONFLICT, "Email already exists"),
    "unsupported_request_type": (status.HTTP_422_UNPROCESSABLE_ENTITY, "Unsupported request type"),
    "rectify_missing_fields": (status.HTTP_422_UNPROCESSABLE_ENTITY, "Missing rectification fields"),
    "no_updates": (status.HTTP_422_UNPROCESSABLE_ENTITY, "No updates provided"),
}


def handle_service_error(exc: ValueError) -> None:
    error_str = str(exc) if exc else "invalid_request"
    status_code, detail = _ERROR_MAP.get(error_str, (status.HTTP_400_BAD_REQUEST, error_str))
    raise HTTPException(status_code=status_code, detail=detail) from exc
