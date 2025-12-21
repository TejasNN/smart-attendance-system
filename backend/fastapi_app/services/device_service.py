from typing import Optional, Dict, Any
from backend.fastapi_app.schemas.provisioning import RegisterRequestDTO, DeviceStatusDTO, TokenDTO
from backend.fastapi_app.db.repos.device_repo import DeviceRepository
from backend.fastapi_app.services.token_service import generate_token, hash_token_bcrypt, verify_token_bcrypt
from desktop_app.utils.utils import current_datetime_utc

class DeviceService:
    """
    Core provisioning engine. No API exposure here — this is pure service layer.
    """
    def __init__(self, postgres, mongo):
        self.repo = DeviceRepository(postgres)
        self.mongo = mongo

    
    def register_request(self, payload: RegisterRequestDTO, registered_by: Optional[int] = None) -> Dict[str, Any]:
        """
        Called when a device first calls register-request.
        If device exists, return that record. Otherwise create a pending record.
        """
        device_uuid = str(payload.device_uuid)
        existing = self.repo.get_by_uuid(device_uuid)
        if existing:
            # log an event and return current status
            self.mongo.log_device_event(existing.get("device_id"), device_uuid, user_id=None, 
                                        event_type="register_requested_duplicate", 
                                        details={"hostname": payload.hostname, 
                                                 "app_version": payload.app_version,
                                                 "os": payload.os})
            return existing
        
        device_id = self.repo.create_register_request(
            device_uuid=device_uuid,
            device_name=payload.hostname,
            assigned_site=None,
            app_version=payload.app_version,
            os_version=payload.os,
            registered_by=registered_by
        )

        # log creation event to mongo
        self.mongo.log_device_event(
            device_id=device_id, 
            device_uuid=device_uuid, 
            user_id=None, 
            event_type="register_requested", 
            details= {
                "hostname": payload.hostname,
                "app_version": payload.app_version,
                "os": payload.os      
        })

        return self.repo.get_by_uuid(device_uuid)
    

    def get_status(self, device_uuid: str) -> DeviceStatusDTO:
        dev = self.repo.get_by_uuid(device_uuid)
        if not dev:
            # If not present, treat as unknown
            return DeviceStatusDTO(status="unknown")
        return DeviceStatusDTO(
            status=dev.get("status"),
            device_id=dev.get("device_id"),
            device_name=dev.get("device_name"),
            assigned_site=dev.get("assigned_site"),
            app_version=dev.get("app_version"),
            os_version=dev.get("os_version"),
            created_at=str(dev.get("created_at")) if dev.get("created_at") else None,
            updated_at=str(dev.get("updated_at")) if dev.get("updated_at") else None
        )
    

    def approve_device(self, device_id: int, approver_employee_id: int) -> bool:
        """
        Approve device: set status to 'active' and log event.
        Token issuance is deferred to fetch_credential called by device.
        """
        # Set status in Postgres
        self.repo.update_status(device_id, "active")

        # fetch device row to log uuid
        dev = self.repo.get_by_id(device_id)
        device_uuid = dev.get("device_uuid") if dev else None

        # fetch registered by user
        registered_by = dev.get("registered_by") if dev else None

        # log into MongoDB
        self.mongo.log_device_event(
            device_id=device_id, 
            device_uuid=device_uuid or "unknown", 
            user_id=approver_employee_id, 
            event_type="approved", 
            details= {
                "approved_by": approver_employee_id
            }
        )
        return True
    

    def generate_and_store_token(self, device_id: int, device_uuid: str) -> str:
        """
        Internal helper: generates token, stores hash in Postgres and logs in Mongo.
        Returns the plaintext token (to be returned once to device).
        """
        token = generate_token(32)
        token_hash = hash_token_bcrypt(token)

        # store hash
        self.repo.set_credential_hash(device_id, token_hash, status="active", 
                                      device_name=None, app_version=None, os_version=None)
        
        # Log event
        self.mongo.log_device_event(
            device_id=device_id, 
            device_uuid=device_uuid, 
            user_id=None,
            event_type="credential_generated",
            details={
                "timestamp": current_datetime_utc()
            }
        )

        return token
    

    def fetch_credential(self, device_uuid: str) -> Optional[TokenDTO]:
        dev = self.repo.get_by_uuid(device_uuid)
        if not dev:
            return None
        
        if dev.get("status") != "active":
            self.mongo.log_device_event(
                device_id=dev.get("device_id"),
                device_uuid=device_uuid,
                user_id=None,
                event_type="credential_fetch_denied",
                details= {
                    "reason": "not_active"
                }
            )
            return None
        
        if dev.get("credential_hash"):
            self.mongo.log_device_event(
                device_id=dev.get("device_id"),
                device_uuid=device_uuid,
                user_id=None,
                event_type="credential_fetch_attempt_after_issue",
                details={}
            )
            return None
        
        # Generate the token
        token = self.generate_and_store_token(dev.get("device_id"), device_uuid)

        # log issuance
        self.mongo.log_device_event(
            device_id=dev.get("device_id"),
            device_uuid=device_uuid,
            user_id=None,
            event_type="credential_issued",
            details={
                "issued_at": current_datetime_utc()
            }
        )
        return TokenDTO(token=token)
    

    def validate_device_token(self, device_uuid: str, token: str) -> bool:
        dev = self.repo.get_by_uuid(device_uuid)
        if not dev or not dev.get("credential_hash"):
            return False
        
        stored_hash = dev.get("credential_hash")
        ok = verify_token_bcrypt(token, stored_hash)

        # log event to mongoDB
        self.mongo.log_device_event(
            device_id=dev.get("device_id"),
            device_uuid=device_uuid,
            user_id=None,
            event_type="device_validation",
            details={
                "outcome": "success" if ok else "failure",
                "attempt": "validate_device_token"
            }
        )
        return ok
    