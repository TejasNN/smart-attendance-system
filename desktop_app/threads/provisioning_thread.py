# desktop_app/threads/provisioning_thread.py
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable
import time
import traceback
from typing import Optional

from desktop_app.api.api_client import ApiClient
from desktop_app.utils.device_info import (
    get_device_uuid, get_hostname, get_app_version, get_os_version
)
from desktop_app.utils.keyring_store import set_value as keyring_set 

class ProvisioningSignals(QObject):
    step = pyqtSignal(str)          # update messages
    success = pyqtSignal(str)       # emits plaintext token
    failure = pyqtSignal(str, str)  # emits failure status
    error = pyqtSignal(str)         # permanent error message
    stopped = pyqtSignal()          # cancelled / stopped

# ============================================================
#  ProvisioningThread
#  Handles: registration → polling → token fetch
# ============================================================

class ProvisioningThread(QRunnable):
    """
    QRunnable that registers device and then polls device status endpoint and 
    when status == 'active' it calls fetch-credential endpoint once. Uses basic requests.
    Emits signals.step to update UI messages, success on token, error on final failure.
    """
    def __init__(
            self,
            api_client: ApiClient, 
            poll_interval: float = 5.0, 
            max_attempts: Optional[int] = 120
        ):
        super().__init__()
        self.signals = ProvisioningSignals()
        self.api = api_client
        self.poll_interval = poll_interval
        self.max_attempts = max_attempts
        self._stopped = False
        self.device_uuid = None

    def stop(self):
        self._stopped = True

    
    def run(self):
        try:
            # ----------------------------------------------------
            # 0) GENERATE AND STORE UUID
            # ----------------------------------------------------
            self.signals.step.emit("Generating device UUID...")
            self.device_uuid = get_device_uuid()

            # store the device_uuid in the keyring
            try:
                keyring_set("device_uuid", self.device_uuid)
                self.signals.step.emit("Device UUID stored securely.")
            except Exception as e:
                self.signals.step.emit(f"Warning: Failed to store device UUID: {e}")
                time.sleep(self.poll_interval)

            # ----------------------------------------------------
            # 1) SEND REGISTER REQUEST ONCE
            # ----------------------------------------------------
            self.signals.step.emit("Sending register request to server...")
            resp = self.api.register_request(
                device_uuid=self.device_uuid,
                hostname=get_hostname(),
                os=get_os_version(),
                app_version=get_app_version()
            )

            # ----------------------------------------------------
            # 2) POLLING LOOP
            # ----------------------------------------------------    
            attempts = 0
            self.signals.step.emit("Waiting for admin approval...")

            while not self._stopped and (self.max_attempts is None or attempts < self.max_attempts):
                attempts += 1

                status_resp = self.api.get_status(device_uuid=self.device_uuid)
                status = (status_resp.get("status") or "").lower()

                # ------------------------------------------------
                # ACTIVE → FETCH TOKEN
                # ------------------------------------------------

                if status == "active":
                    # attempt to fetch the credentials once
                    self.signals.step.emit("Device approved by Admin -- Fetching credentials...")
                    token_resp = self.api.fetch_credential(device_uuid=self.device_uuid)
                    token = token_resp.get("token")

                    if not token:
                        self.signals.error.emit("Server returned empty token.")
                        return
                    
                    try:
                        keyring_set("device_token", token)
                        self.signals.step.emit("Device token stored securely.")
                    except Exception as e:
                        self.signals.step.emit(f"Warning: Failed to store device token: {e}")

                    self.signals.success.emit(token)
                    return
                
                # ------------------------------------------------
                # PENDING OR UNKNOWN
                # ------------------------------------------------
                
                elif status in ("pending", "unknown", ""):
                    self.signals.step.emit(f"Device status is {status} - Awaiting admin approval \
                                           - (attempt {attempts}) -- retrying...")
                    time.sleep(self.poll_interval)
                    continue
                
                # ------------------------------------------------
                # REJECTED → SIGNAL FAILURE
                # ------------------------------------------------
                
                elif status == "rejected":
                    self.signals.failure.emit("Device rejected - Please contact the administrator.", status)
                    return
                        
                # ------------------------------------------------
                # STATUS -> None (Credential already exists)
                # ------------------------------------------------

                elif status is None:
                    self.signals.step.emit(f"Credential already exists.")
                    return 
                
                # ------------------------------------------------
                # STILL PENDING
                # ------------------------------------------------
                else:
                    self.signals.step.emit(f"Waiting for approval... (attempt {attempts})")
                    time.sleep(self.poll_interval)
                    continue
                
            # TIMEOUT
            if self._stopped:
                self.signals.stopped.emit()
            else:
                self.signals.error.emit("Timeout waiting for approval.")
                
        except Exception as e:
            traceback.print_exc()
            self.signals.error.emit(f"Unexpected error: {str(e)}")
