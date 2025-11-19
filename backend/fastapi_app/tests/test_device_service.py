# backend/app/tests/test_device_service.py
# Lightweight smoke test for device service.

import os
from uuid import uuid4
from backend.fastapi_app.services.device_service import DeviceService
from backend.fastapi_app.schemas.provisioning import RegisterRequestDTO

def run_smoke():
    svc = DeviceService()

    u = uuid4()

    payload = RegisterRequestDTO(device_uuid=u, hostname="Test-PC", os="TestOS", app_version="0.0.1")
    print("Registering device...", u)
    
    dev = svc.register_request(payload)
    print("Register returned (partial):", {k: dev.get(k) 
                                           for k in ("device_id", "device_uuid", "status")} 
                                           if isinstance(dev, dict) else dev)
    
    status = svc.get_status(str(u))
    print("Status:", status.model_dump_json())

    # get device_id
    device_id = None
    if isinstance(dev, dict):
        device_id = dev.get("device_id")
    if not device_id:
        print("No device_id found. Check DB insertion.")
        return

    print("Approving device_id:", device_id)
    svc.approve_device(device_id, approver_employee_id=1)

    token_obj = svc.fetch_credential(str(u))
    print("Token issued (first fetch):", token_obj.model_dump() if token_obj else None)

    token_obj2 = svc.fetch_credential(str(u))
    print("Second fetch (should be None):", token_obj2)


if __name__ == "__main__":
    run_smoke()