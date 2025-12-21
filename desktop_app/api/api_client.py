# desktop_app/api_client/api_client.py
"""
Small ApiClient wrapper around requests.Session for the provisioning flow.
Centralizes timeouts, error messages and endpoints used by the ProvisioningThread.
"""
import requests
from typing import Optional, Dict, Any

DEFAULT_TIMEOUT = 8     # seconds

class ApiClient:
    """
    Central API client for desktop application.
    All HTTP traffic MUST go through _request().
    """
    def __init__(self, base_url: str, session: Optional[requests.Session] = None,
                 timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

    # --------------------------------------------------
    # Core request handler (single source of truth)
    # --------------------------------------------------
    def _request(self, method: str, path: str, *, json: Optional[dict] = None,
                 params: Optional[dict] = None, headers: Optional[dict] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.request(
                method=method,
                url=url,
                json=json,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            if resp.text.strip() == "":
                return {}
            return resp.json()
        
        except requests.HTTPError as e:
            # Try extracting FastAPI error message
            try:
                detail = resp.json().get("detail")
            except Exception:
                detail = resp.text or "HTTP Error"

            raise RuntimeError(f"HTTP {resp.status_code}: {detail}") from e
        
        except requests.RequestException as e:
            raise RuntimeError(f"Network error: {str(e)}") from e

    # --------------------------------------------------
    # Device provisioning endpoints
    # --------------------------------------------------    

    def register_request(self, device_uuid: str, hostname: Optional[str] = None,
                         os: Optional[str] = None, 
                         app_version: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            method="POST",
            path="/devices/register-request",
            json={
                "device_uuid": device_uuid,
                "hostname": hostname,
                "os": os,
                "app_version": app_version,
            },
        )
    

    def get_status(self, device_uuid: str) -> Dict[str, Any]:
        return self._request(
            method="GET",
            path=f"/devices/status/{device_uuid}",
        )
    

    def fetch_credential(self, device_uuid: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/devices/fetch-credential",
            json={"device_uuid": device_uuid},
        )
        
    # --------------------------------------------------
    # Operator authentication
    # --------------------------------------------------

    def operator_login(self, device_uuid: str, device_token: str,
                       username: str, password: str):
        return self._request(
            method="POST",
            path=f"/auth/operator/login",
            json={
                "device_uuid": device_uuid,
                "device_token": device_token,
                "username": username,
                "password": password,
            },
        )
        