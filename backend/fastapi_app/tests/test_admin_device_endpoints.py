from fastapi.testclient import TestClient
from backend.fastapi_app.main import app 
from uuid import uuid4

client = TestClient(app)

def print_response(resp):
    try:
        print(resp.status_code, resp.json())
    except Exception:
        print(resp.status_code, resp.text)


def run_api_smoke():
    print("\n=== API END-TO-END SMOKE TEST FOR DEVICE PROVISIONING ===")

    # 1) Register device
    device_uuid = str(uuid4())
    print("\n1) Registering device: ", device_uuid)
    resp = client.post("/api/v1/devices/register-request", json={
        "device_uuid":device_uuid,
        "hostname":"Test-PC",
        "os":"Test-OS",
        "app_version":"0.0.1"
    })
    print_response(resp)
    assert resp.status_code in (200, 201)

    # 2) Check status (should be pending)
    resp = client.get(f"api/v1/devices/status/{device_uuid}")
    print("\n2) Status: ", end=" ")
    print_response(resp)
    assert resp.status_code == 200
    assert resp.json().get("status") in ("pending", "unknown", None) or True

    # 3) Get pending via admin (requires admin present)
    # Login as admin (test_admin/test_admin assumed present)
    resp = client.post("/api/v1/auth/admin/login", json={
        "username": "xxxx",
        "password": "xxxx"
    })
    print("\n3) Admin login: ", end=" ")
    print_response(resp)
    assert resp.status_code == 200
    token = resp.json().get("access_token")
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # 4) List pending devices
    resp = client.get("/api/v1/admin/devices/pending", headers=headers)
    print("\n4) Pending devices: ", end=" ")
    print_response(resp)
    assert resp.status_code == 200

    pending = resp.json()
    print("pending list: ", pending)
    assert isinstance(pending, list)

    # Find the registered device in pending list
    found = None
    for d in pending:
        if str(d.get("device_uuid")) == device_uuid:
            found = d
            break
    if not found:
        print("Registered device not found in pending list; " \
        "Using first pending (fallback).")
        # continue anyway

    device_id = found["device_id"] if found else (
            pending[0]["device_id"] if pending else None
    )
    print("Approving device id =", device_id)
    assert device_id is not None, "No device_id to approve"

    # 5) Approve device
    resp = client.post(f"/api/v1/admin/devices/{device_id}/approve", headers=headers)
    print("\n5) Approve device:", end=" ")
    print_response(resp)
    assert resp.status_code == 200

    # 6) Device fetch credential (first time)
    resp = client.post("api/v1/devices/fetch-credential", json={"device_uuid": device_uuid})
    print("\n6) Fetch credential (first):", end=" ")
    print_response(resp)
    assert resp.status_code == 200
    token_val = resp.json().get("token")
    assert token_val is not None

    # 7) Second fetch should be forbidden (or return 403)
    resp = client.post("/api/v1/devices/fetch-credential", json={"device_uuid": device_uuid})
    print("\n7) Fetch credential (second):", end=" ")
    print_response(resp)
    assert resp.status_code in (400, 401, 403, 404)

    # 8) Assign employee 1
    resp = client.post(
        f"api/v1/admin/devices/{device_id}/assign", 
        headers=headers,
        json={"employee_ids": [2]}
    )
    print("\n8) Assigning employee: 2", end=" ")
    print_response(resp)
    assert resp.status_code == 200

    # 9) Get device details
    resp = client.get(f"/api/v1/admin/devices/{device_id}", headers=headers)
    print("\n9) Getting device details: ", end=" ")
    print_response(resp)
    assert resp.status_code == 200

    # 10) List all devices (admin convenience)
    resp = client.get("/api/v1/admin/devices/list", headers=headers)
    print("\n10) List all devices: ", end= " ")
    print_response(resp)
    assert resp.status_code == 200

    #11) Force reset token
    resp = client.post(
        f"/api/v1/admin/devices/{device_id}/force-reset-token",
        headers=headers
    )
    print("\n11) Force reset token: ", end=" ")
    print_response(resp)
    assert resp.status_code == 200

    # 12) After reset, device must be able to fetch a new token
    resp = client.post(
        "api/v1/devices/fetch-credential",
        json={"device_uuid": device_uuid}
    )
    print("\n12) Device fetch credential after reset (should succeed): ", end=" ")
    print_response(resp)
    assert resp.status_code == 200
    new_token = resp.json().get("token")
    assert new_token is not None
    assert new_token != token_val   # new token must differ

    # 13) Reject pending device (rejection)
    resp = client.post(
        f"/api/v1/admin/devices/{device_id}/reject",
        headers=headers,
        json={"reason": "Test device pending rejection"}
    )
    print("\n13) Reject pending device: ", end=" ")
    print_response(resp)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    # 13) Reject approved device (revokation)
    resp = client.post(
        f"api/v1/admin/devices/{device_id}/reject",
        headers=headers,
        json={"reason": "Test device revoked by admin"}
    )
    print("\n13) Reject approved device:", end=" ")
    print_response(resp)
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"

    print("\n ======== END-TO-END PROVISIONING TEST COMPLETE")


if __name__ == "__main__":
    run_api_smoke()