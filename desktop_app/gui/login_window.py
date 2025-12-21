# smart_attendance/gui/login_window.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
    QMessageBox, QHBoxLayout
)
from PyQt6.QtCore import pyqtSignal
from desktop_app.utils.keyring_store import get_value as keyring_get
from desktop_app.api.api_client import ApiClient

class LoginWindow(QDialog):
    """
    Simple modal dialog for operator login. Emits login_success(session_token, employee_id, username)
    """
    login_success = pyqtSignal(str, int, str)

    def __init__(self, api_client: ApiClient, parent = None):
        super().__init__(parent)
        self.api = api_client
        self.setWindowTitle("Operator Login")
        self.setModal(True)
        self._build_ui()


    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        # Buttons
        row = QHBoxLayout()
        self.btn_login = QPushButton("Login")
        self.btn_login.clicked.connect(self._do_login)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        row.addStretch()
        row.addWidget(self.btn_login)
        row.addWidget(self.btn_cancel)
        layout.addLayout(row)

    
    def _do_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "Validation", "Username and password are required")
            return
        
        # Device credentials (from keyring)
        device_uuid = keyring_get("device_uuid")
        device_token = keyring_get("device_token")
        if not device_uuid or not device_token:
            QMessageBox.critical(self, "Device not provisioned", "Device credential missing. Re-run provisioning.")
            self.reject()
            return
        
        try:
            # Call api client operator login (expects dict with session token)
            resp = self.api.operator_login(device_uuid=device_uuid, device_token=device_token,
                                           username=username, password=password)
        except Exception as e:
            QMessageBox.critical(self, "Network", f"Login failed: {e}")
            return
        
        session_token = resp.get("session_token")
        employee_id = resp.get("employee_id")
        operator_username = resp.get("username") or username

        if not session_token or not employee_id:
            QMessageBox.critical(self, "Login failed", "Server returned invalid login response")
            return

        # Emit success and close dialog
        self.login_success.emit(session_token, employee_id, operator_username)
        self.accept() 
        