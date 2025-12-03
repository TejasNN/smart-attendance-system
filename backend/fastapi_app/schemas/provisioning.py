# backend/app/schemas/provisioning.py
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

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


class FetchCredentialRequestDTO(BaseModel):
    device_uuid: UUID


class AssignRequestDTO(BaseModel):
    employee_ids: List[int] = Field(..., min_items=1)


class PendingDeviceDTO(BaseModel):
    device_id: int
    device_uuid: str
    device_name: Optional[str] = None
    assigned_site: Optional[str] = None
    app_version: Optional[str] = None
    os_version: Optional[str] = None
    status: Optional[str] = None
    requested_at: Optional[str] = None


class DeviceLogDTO(BaseModel):
    device_id: int
    device_uuid: str
    user_id: Optional[int]
    event_type: Optional[str]
    details: Optional[dict]
    timestamp: datetime

    def to_mongo(self):
        return {
            "device": {
                "id": self.device_id,
                "uuid": self.device_uuid
            },
            "user_id": self.user_id,
            "event_type": self.event_type,
            "details": self.details,
            "timestamp": self.timestamp
        }
