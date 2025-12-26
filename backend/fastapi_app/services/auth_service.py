# backend/fastapi_app/services/auth_service.py
from typing import Optional, Dict, Any
from backend.fastapi_app.db.repos.user_repo import UserRepository
from backend.fastapi_app.db.repos.assignment_repo import AssignmentRepository
from backend.fastapi_app.db.repos.device_repo import DeviceRepository
from backend.fastapi_app.services.device_service import DeviceService
from backend.fastapi_app.core.security import verify_password, create_jwt_token

class AuthService:
    """
    Handles admin and operator authentication.
    """

    def __init__(self, postgres_db=None, mongo_db=None):
        self.user_repo = UserRepository(postgres_db)
        self.assignment_repo = AssignmentRepository(postgres_db)
        self.device_repo = DeviceRepository(postgres_db)
        self.device_service = DeviceService(postgres_db, mongo_db)

    
    #----------- Admin login ---------------
    def admin_login(self, username: str, password: str) -> Optional[str]:
        user = self.user_repo.get_by_username(username)
        if not user:
            return None
        if user.get("role") != "admin" or not user.get("is_active"):
            return None
        if not verify_password(password, user.get("password_hash")):
            return None
        
        claims = {
            "employee_id": user["employee_id"], 
            "role": "admin",
            "username": user["username"],
        }
        token = create_jwt_token(claims)
        return token
    

    # ---------- Operator login (device + assignment checks) -------------
    def operator_login(self, device_uuid: str, device_token: str, username: str, 
                       password: str) -> Optional[Dict[str, Any]]:
        # fetch user
        user = self.user_repo.get_by_username(username)
        if not user:
            return None
        if user.get("role") != "operator" or not user.get("is_active"):
            return None
        if not verify_password(password, user.get("password_hash")):
            return None
        
        # validate device token and status
        device_row = self.device_repo.get_by_uuid(device_uuid)
        if not device_row:
            return None
        
        # check device token validity
        if not self.device_service.validate_device_token(device_uuid, device_token):
            return None
        
        # check assignment: device_id and employee_id must be linked
        device_id = device_row.get("device_id")
        employee_id = user.get("employee_id")
        if not self.assignment_repo.is_user_assigned_to_device(employee_id, device_id):
            return None
        
        # create session token (short lived)
        claims = {
            "employee_id": employee_id,
            "role": "operator",
            "username": user["username"],
            "device_id": device_id
        }
        session_token = create_jwt_token(claims)     # default expiry applies
        return {
            "session_token": session_token,
            "employee_id": employee_id,
            "username": user.get("username"),
            "name": user.get("employee_name")
        }
    

    def close(self):
        try:
            self.user_repo.close()
            self.assignment_repo.close()
            self.device_repo.close()
        except Exception:
            pass