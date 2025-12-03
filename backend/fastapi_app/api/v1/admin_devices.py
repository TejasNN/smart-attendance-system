# fastapi_app/api/v1/admin_devices.py
from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List, Dict, Any
from backend.fastapi_app.api.deps import admin_required
from backend.fastapi_app.services.admin_service import AdminService
from backend.fastapi_app.schemas.provisioning import PendingDeviceDTO, AssignRequestDTO

router = APIRouter(prefix="/api/v1/admin/devices", tags=["admin_devices"])
_admin_svc = AdminService()

@router.get("/pending", response_model=List[PendingDeviceDTO], dependencies=[Depends(admin_required)])
def list_pending_devices():
    """
    Return a list of devices with status = 'pending'
    """
    try:
        rows = _admin_svc.list_pending_devices(limit=100)
        return rows
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch pending devices"
        )


@router.get("/list", dependencies=[Depends(admin_required)])
def get_all_devices():
    try:
        device_list = _admin_svc.list_all_devices(limit=100)
        if not device_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Devices not found"
            )
        return device_list
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch devices")
    

@router.get("/{device_id}", dependencies=[Depends(admin_required)])
def get_device_details(device_id: int = Path(..., gt=0)):
    try:
        details = _admin_svc.get_device_details(device_id)
        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        return details
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch device details")
    

@router.post("/{device_id}/approve", dependencies=[Depends(admin_required)])
def approve_device(device_id: int = Path(..., gt=0), claims: Dict[str, Any] = Depends(admin_required)):
    """
    Admin approves device. Approval sets status = 'active'.
    Token issuance is deferred to device fetch (DeviceService.fetch_credential will create token once).
    """
    approver_employee_id = claims.get("employee_id")
    try:
        ok = _admin_svc.approve_device(device_id, approver_employee_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to approve device"
            )
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve device"
        )
    

@router.post("/{device_id}/reject", dependencies=[Depends(admin_required)])
def reject_device(device_id: int = Path(..., gt=0), claims: Dict[str, Any] = Depends(admin_required)):
    try:
        device_status = _admin_svc.reject_device(device_id, claims.get("employee_id"))
        if not device_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Failed to reject device"
            )
        return {
            "status": device_status, 
            "device_id": device_id
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject device"
        )
    

@router.post("/{device_id}/force-reset-token", dependencies=[Depends(admin_required)])
def force_reset_token(device_id: int = Path(..., gt=0), claims: Dict[str, Any] = Depends(admin_required)):
    try:
        ok = _admin_svc.force_reset_token(device_id, claims.get("employee_id"))
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Reset failed"
            )
        return {
            "status": "token_reset", 
            "device_id": device_id
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset token"
        )
    

@router.post("/{device_id}/assign", dependencies=[Depends(admin_required)])
def assign_users(device_id: int = Path(..., gt=0), payload: AssignRequestDTO = None,
                 claims: Dict[str, Any] = Depends(admin_required)):
    """
    Assign one or more operator employees to a device.
    Payload: { "employee_ids": [1,2,3] }
    """
    if not payload or not payload.employee_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="employee ids required"
        )
    
    try:
        res = _admin_svc.assign_users(device_id, payload.employee_ids, assigned_by=claims.get("employee_id"))
        return res
    except Exception:
        raise
    except ValueError as ve:
        if str(ve) == "device_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign employees to device"
        )
    