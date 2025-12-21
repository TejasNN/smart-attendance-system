# fastapi_app/api/v1/devices.py
from fastapi import Depends, APIRouter, HTTPException, status
from backend.fastapi_app.schemas.provisioning import (
    RegisterRequestDTO, DeviceStatusDTO, FetchCredentialRequestDTO, TokenDTO
)
from backend.fastapi_app.services.device_service import DeviceService
from backend.fastapi_app.api.deps import get_device_service

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.post("/register-request", status_code=status.HTTP_201_CREATED)
def register_request(payload: RegisterRequestDTO, svc: DeviceService = Depends(get_device_service)):
    """
    Device first-run: create or update a pending register-request.
    Returns a minimal acknowledgment; device should poll /status.
    """
    try:
        device_record = svc.register_request(payload)
        return {
            "status": device_record.get("status", "pending"),
            "device_uuid": device_record.get("device_uuid"),
            "device_id": device_record.get("device_id"),
            "message": "Request recorded"
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record register request"
        )
    

@router.get("/status/{device_uuid}", response_model=DeviceStatusDTO)
def get_status(device_uuid: str, svc: DeviceService = Depends(get_device_service)):
    """
    Device polls this endpoint to check approval status.
    """
    try:
        status_dto = svc.get_status(device_uuid)
        return status_dto
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch device status"
        )
    

@router.post("/fetch-credential", response_model=TokenDTO)
def fetch_credential(payload: FetchCredentialRequestDTO, svc: DeviceService = Depends(get_device_service)):
    """
    Device calls this once /status returns active. This returns a plaintext token once,
    and subsequent calls are rejected. Service handles token generation/storage.
    """
    try:
        token_dto = svc.fetch_credential(str(payload.device_uuid))
        if not token_dto:
            # fetch failed (not active, or already delivered or device missing)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Credential not available"
            )
        return TokenDTO(token=token_dto.token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch credential"
        )
