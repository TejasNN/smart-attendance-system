# backend/fastapi_app/tests/test_auth_service.py
# NOTE: This is a lightweight smoke/helper test. It requires DB seeded with a test admin and operator.
import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.append(BASE_DIR)

from backend.fastapi_app.services.auth_service import AuthService

def run_smoke_admin(username, password):
    svc = AuthService()
    token = svc.admin_login(username, password)
    print("Admin token: ", token)
    svc.close()


def run_smoke_operator(device_uuid, device_token, username, password):
    svc = AuthService()
    res = svc.operator_login(device_uuid, device_token, username, password)
    print("Operator login result: ", res)
    svc.close()


if __name__ == "__main__":
    run_smoke_admin("xxxx", "xxxxxx")