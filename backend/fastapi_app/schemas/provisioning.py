# backend/app/schemas/provisioning.py
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class RegisterRequestDTO(BaseModel):
    device_uuid: UUID
    hostname: Optional[str] = None
    os: Optional[str] = None
    app_version: Optional[str] = None


class DeviceStatusDTO(BaseModel):
    status: str
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    assigned_site: Optional[str] = None
    app_version: Optional[str] = None
    os_version: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TokenDTO(BaseModel):
    token: str
