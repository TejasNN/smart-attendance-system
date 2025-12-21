import platform
import uuid
from desktop_app.config import APP_VERSION

def get_device_uuid() -> str:
    """
    Generate a new UUID. Persisting is the responsibility of the provisioning flow
    (we will store it in keyring).
    """
    return str(uuid.uuid4())


def get_hostname() -> str:
    return platform.node()


def get_os_version() -> str:
    return f"{platform.system()}_{platform.release()}"


def get_app_version() -> str:
    """
    Read application version from config so it's configurable per-release.
    Fallback to '1.0.0' if not set.
    """
    try:
        return APP_VERSION.get("app_version", "1.0.0")
    except Exception:
        return "1.0.0"