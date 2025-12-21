import keyring
import json
from typing import Optional

SERVICE_NAME = "smart_attendance_device"

def set_value(key: str, value) -> None:
    """
    store JSON-serializable value under service:key in OS keyring.
    """
    try:
        payload = json.dumps(value)
        keyring.set_password(SERVICE_NAME, key, payload)
    except Exception:
        raise


def get_value(key: str, default=None):
    try:
        value = keyring.get_password(SERVICE_NAME, key)
        if not value:
            return default
        return json.loads(value)
    except Exception:
        return default
    

def delete_value(key: str):
    try:
        keyring.delete_password(SERVICE_NAME, key)
    except Exception:
        raise
