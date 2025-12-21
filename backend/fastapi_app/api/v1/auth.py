# backend/fastapi_app/api/v1/auth.py
from fastapi import Depends, APIRouter, HTTPException, status
from backend.fastapi_app.schemas.auth import (
    AdminLoginRequest, AdminLoginResponse, OperatorLoginRequest,
    OperatorLoginResponse
)
from backend.fastapi_app.services.auth_service import AuthService
from backend.fastapi_app.api.deps import get_auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/admin/login", response_model=AdminLoginResponse)
def admin_login(req: AdminLoginRequest, svc: AuthService = Depends(get_auth_service)):
    token = svc.admin_login(req.username, req.password)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid credentials")
    return AdminLoginResponse(access_token=token)


@router.post("/operator/login", response_model=OperatorLoginResponse)
def operator_login(req: OperatorLoginRequest, svc: AuthService = Depends(get_auth_service)):
    res = svc.operator_login(req.device_uuid, req.device_token, 
                                   req.username, req.password)
    if not res:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid credentials")
    return OperatorLoginResponse(
        session_token=res["session_token"],
        employee_id=res["employee_id"],
        username=res["username"],
        name=res.get("name")
    )