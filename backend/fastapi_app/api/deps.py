# backend/fastapi_app/api/deps.py
import logging
from types import SimpleNamespace
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.fastapi_app.core.security import decode_jwt_token
from backend.fastapi_app.db.postgres_db import PostgresDB
from backend.fastapi_app.db.mongo_db import MongoDB
from backend.fastapi_app.db.repos.device_repo import DeviceRepository
from backend.fastapi_app.db.repos.assignment_repo import AssignmentRepository
from backend.fastapi_app.services.device_service import DeviceService
from backend.fastapi_app.services.admin_service import AdminService
from backend.fastapi_app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)

# -----------------------
# Database Dependencies
# -----------------------

def get_postgres(request: Request):
    db = getattr(request.app.state, "postgres", None)
    if not db:
        raise RuntimeError("Postgres not initialized")
    return db


def get_mongo(request: Request):
    db = getattr(request.app.state, "mongo", None)
    if not db:
        raise RuntimeError("Mongo not initialized")
    return db

# -----------------------
# Service Dependencies
# -----------------------

def get_device_service(
    pg = Depends(get_postgres),
    mg = Depends(get_mongo),
):
    return DeviceService(pg, mg)


def get_admin_service(
    pg = Depends(get_postgres),
    mg = Depends(get_mongo),
):
    return AdminService(pg, mg)


def get_auth_service(
    pg = Depends(get_postgres),
    mg = Depends(get_mongo),
):
    return AuthService(pg, mg)


def admin_required(creds: HTTPAuthorizationCredentials = 
                   Depends(bearer_scheme)) -> Dict[str, Any]:
    """
    FastAPI dependency that:
      1) extracts Bearer token
      2) decodes JWT
      3) ensures claim role == 'admin'
      4) verifies the admin user exists in Postgres and is_active == TRUE

    Returns the decoded claims (so handlers can access employee_id, username, etc.)
    Raises HTTPException(401/403) on failure.
    """
    # 1. Token present?
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Authorization credentials missing"
        )
    
    token = creds.credentials
    
    # 2. Decode JWT
    try:
        claims = decode_jwt_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid or expired token"
        )
    
    # Role check
    role = claims.get("role")
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin role required"
        )
    
    employee_id = claims.get("employee_id")
    if employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token: missing employee id"
        )
    
    # validate admin in Postgres
    pg = PostgresDB()

    try:
        row = pg.get_user_status(employee_id)
    except Exception:
        # close connection and re-raise as 500
        try:
            pg.cursor.close()
            pg.conn.close()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Database error while verifying admin"
            )
    finally:
        # cleanup connection
        try:
            pg.cursor.close()
            pg.conn.close()
        except Exception:
            pass

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Admin user not found"
        )
    
    if not row.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin account is not active"
        )
    
    # Optionally we can return a consolidated dict of claims + username
    claims["username"] = row.get("username")

    return claims


def operator_required(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    request: Request = None,
    x_device_uuid: Optional[str] = Header(None, alias="X-Device-UUID"),
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token")
) -> Dict[str, Any]:
    """
    FastAPI dependency that verifies BOTH:
      - device identity + device token + device status
      - operator session JWT + operator active + assignment to device

    Expected headers:
      X-Device-UUID: <uuid string>
      X-Device-Token: <device token>
      Authorization: Bearer <session_jwt>

    On success returns a dict with consolidated claims:
      {
        "employee_id": int,
        "username": str,
        "role": "operator",
        "device_id": int,
        "device_uuid": str
      }

    Raises HTTPException(401/403/500) on failures.
    """
    # 1) Required headers present?
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session credentials missing"
        )
    session_token = creds.credentials

    if not x_device_uuid or not x_device_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device headers missing (X-device_UUID '/ X-Device_Token)"
        )
    
    # 2) decode session JWT
    try:
        session_claims = decode_jwt_token(session_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token"
        )
    
    # role check
    if session_claims.get("role") != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator role required"
        )
    
    employee_id = session_claims.get("employee_id")
    if employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token: missing employee_id"
        )
    
    # 3) Validate device row and status
    device_repo = DeviceRepository()
    device_service = DeviceService()
    assignment_repo = AssignmentRepository()
    pg = PostgresDB()

    device_row = device_repo.get_by_uuid(x_device_uuid)
    if not device_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device not found"
        )
    
    if device_row.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device not active"
        )
    
    # validate device token (bcrypt compare). DeviceService handles logging.
    ok = device_service.validate_device_token(x_device_uuid, x_device_token)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device token"
        )
    
    # 4) Validate operator exists & is active in Postgres
    try:
        user_row = pg.get_user_status(employee_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while validating operator"
        )
    finally:
        try:
            pg.cursor.close()
            pg.conn.close()
        except Exception as e:
            logger.exception(f"Failed to close the postgres connection: {e}")

    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operator user not found"
        )
    
    if not user_row.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator account is not active"
        )
        
    # 5) Ensure the session tokens's device_id (if present) matches this device_id
    session_device_id = session_claims.get("device_id")
    device_id = device_row.get("device_id")
    if session_device_id is not None and int(session_device_id) != int(device_id):
        # possible token misuse / bound-to-different-device
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session token bound to different device"
        )
    
    # 6) Check assingment: employee must be assigned to device
    assigned = assignment_repo.is_user_assigned_to_device(employee_id, device_id)
    if not assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator not assigned to this device"
        )
    
    # 7) All checks passed: rerun consolidated claims (attach username too)
    session_claims["username"] = user_row.get("username")
    session_claims["device_id"] = device_id
    session_claims["device_uuid"] = x_device_uuid

    return SimpleNamespace(**session_claims)
