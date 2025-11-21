# backend/fastapi_app/schemas/auth.py
from pydantic import BaseModel
from typing import Optional

# Admin login
class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Operator login
class OperatorLoginRequest(BaseModel):
    device_uuid: str
    device_token: str
    username: str
    password: str


class OperatorLoginResponse(BaseModel):
    session_token: str
    employee_id: int
    username: str
    name: Optional[str] = None