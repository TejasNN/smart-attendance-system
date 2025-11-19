# backend/fastapi_app/db/repos/device_repo.py
from typing import Optional, Dict, Any
from backend.fastapi_app.db.postgres_db import PostgresDB

class DeviceRepository:
    """
    Thin repository wrapper around PostgresDB for device-specific operations.
    Uses your existing PostgresDB class so SQL is centralized there.
    """

    def __init__(self):
        self._db = PostgresDB()

    
    def create_register_request(self, device_uuid: str, device_name: str = None,
                                assigned_site: str = None, app_version: str = None,
                                os_version: str = None, registered_by: int = None) -> Optional[int]:
        return self._db.add_device_registration(device_uuid, device_name, assigned_site, 
                                                app_version, os_version, registered_by)
    

    def get_by_uuid(self, device_uuid: str) -> Optional[Dict[str, Any]]:
        return self._db.get_device_by_uuid(device_uuid)
    

    def get_by_id(self, device_id: int) -> Optional[Dict[str, Any]]:
        return self._db.get_device_by_id(device_id)
    

    def set_credential_hash(self, device_id: int, credential_hash: str, status: str = "active",
                            device_name: str = None, app_version: str = None, os_version: str = None):
        self._db.set_device_credential(device_id, credential_hash, status, device_name, app_version, os_version)

    
    def update_status(self, device_id: int, status: str):
        self._db.update_device_status(device_id, status)

    
    def device_has_credential(self, device_uuid: str) -> bool:
        dev = self.get_by_uuid(device_uuid)
        if not dev:
            return False
        return bool(dev.get("crendential_hash"))
    

    def close(self):
        try:
            self._db.close()
        except Exception:
            pass
