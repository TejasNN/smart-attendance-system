# smart_attendance/gui/main_window.py
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import QThreadPool, QTimer
from functools import partial

from desktop_app.gui.attendance_window import AttendanceWindow
from desktop_app.gui.logs_window import LogsWindow
from desktop_app.gui.dashboard_ui import DashboardUI
from desktop_app.utils.utils import center_window

from desktop_app.threads.provisioning_thread import ProvisioningThread
from desktop_app.api.api_client import ApiClient
from desktop_app.utils.keyring_store import get_value as keyring_get, set_value as keyring_set
from desktop_app.config import BASE_URL


class MainWindow(QMainWindow):
    def __init__(self, post_db, mongo_db, parent=None):
        super().__init__(parent)
        self.post_db = post_db
        self.mongo_db = mongo_db
        self.setWindowTitle("Smart Attendance System")
        self.setGeometry(200, 200, 1200, 700)
        center_window(self)

        # Integrate the new dashboard UI
        self.dashboard_ui = DashboardUI()
        self.setCentralWidget(self.dashboard_ui)

        self.dashboard_ui.content_stack.setObjectName("contentStack")

        # add other windows into the dashboard's content stack so they render inside central frame
        # page 0 is the dashboard itself (already present). We'll add attendance, logs as pages.
        # Create instances but do NOT show as standalone windows; add them as widgets to stack.
        self.attendance_page = AttendanceWindow(self.post_db, self.mongo_db)
        self.logs_page = LogsWindow(self.mongo_db)

        # Add pages to the stack; store their page indexes
        self.dashboard_ui.content_stack.addWidget(self.attendance_page)
        self.page_attendance_idx = self.dashboard_ui.content_stack.indexOf(self.attendance_page)

        self.dashboard_ui.content_stack.addWidget(self.logs_page)
        self.page_logs_idx = self.dashboard_ui.content_stack.indexOf(self.logs_page)

        # threadpool for background tasks
        self.thread_pool = QThreadPool.globalInstance()

        # Wire up sidebar buttons
        self._connect_sidebar_buttons()

        self.dashboard_ui.content_stack.setCurrentIndex(self.page_attendance_idx)
        self.dashboard_ui.highlight_active_button(self.dashboard_ui.btn_attendance)

        # Configure loader callbacks so DashboardUI buttons work
        self.dashboard_ui.provision_overlay.retry_requested.connect(self._retry_provisioning_flow)
        self.dashboard_ui.provision_overlay.cancel_requested.connect(self._cancel_provisioning_flow)

        # login wiring
        self.dashboard_ui.login_submitted.connect(
            lambda username, password: self.handle_login_submission(username, password)
        )

        self.dashboard_ui.login_cancel_requested.connect(
            lambda: self.close()
        )

        self.dashboard_ui.forgot_password_requested.connect(
            lambda: self.dashboard_ui.show_overlay_feedback(
                "Please contact your administrator to reset your password", "info"
            )
        )

        # worker handle
        self._provision_worker = None
        self._api_client = ApiClient(BASE_URL.rstrip("/"))

        # check keyring for device_uuid and token
        device_uuid = keyring_get("device_uuid")
        device_token = keyring_get("device_token")

        # If not provisioned, start provisioning flow; else go to login
        if not device_uuid or not device_token:
            # device not provisioned -> run provisioning
            self.start_provisioning_flow()
        else:
            # Procedd to operator login (device already provisioned)
            self.open_login_window()


    def _connect_sidebar_buttons(self):
        btns = {
            self.dashboard_ui.btn_attendance: self.page_attendance_idx,
            self.dashboard_ui.btn_logs: self.page_logs_idx,
        }
        for btn, idx in btns.items():
            try:
                btn.clicked.disconnect()
            except Exception:
                pass
            btn.clicked.connect(partial(self._switch_and_highlight, idx, btn))


    def _switch_and_highlight(self, page_idx, button):
        self.dashboard_ui.content_stack.setCurrentIndex(page_idx)
        self.dashboard_ui.highlight_active_button(button)

    # --------------- Provisioning flow ---------------
    def start_provisioning_flow(self):
        """
        Called when device is not yet provisioned.
        Shows loader overlay and starts ProvisioningThread worker.
        """
        # Show loader and waiting controls
        self.dashboard_ui.show_loader("Preparing device registration...")
        self.dashboard_ui.provision_overlay.set_state_waiting()

        # Create worker
        worker = ProvisioningThread(api_client=self._api_client)
        
        # Connect worker
        worker.signals.step.connect(lambda message: self.dashboard_ui.update_loader(message))
        worker.signals.success.connect(self._on_credential_fetched)
        worker.signals.failure.connect(self._on_provisioning_failure)
        worker.signals.error.connect(self._on_credential_error)
        worker.signals.stopped.connect(lambda: self.dashboard_ui.update_loader("Provisioning stopped"))
        
        # Store reference and start
        self._provision_worker = worker
        self.thread_pool.start(worker)

    
    def _retry_provisioning_flow(self):
        # Stop running worker (if any) and start a fresh one
        if self._provision_worker:
            try:
                self._provision_worker.stop()
            except Exception:
                raise
            self._provision_worker = None

        self.dashboard_ui.update_loader("Retrying provisioning…")
        self.dashboard_ui.provision_overlay.set_state_waiting()
        
        # restart
        self.start_provisioning_flow()


    def _cancel_provisioning_flow(self):
        if self._provision_worker:
            try:
                self._provision_worker.stop()
            except Exception:
                raise
        self._provision_worker = None
        self.dashboard_ui.show_waiting_controls(False)
        self.dashboard_ui.hide_loader()
        QTimer.singleShot(100, self.close)


    def _on_credential_fetched(self, token: str):
        """
        Called when provisioning thread successfully fetched token.
        Token may already be stored by the thread; ensure keyring has it.
        """
        try:
            # Ensure token present in keyring (thread should have saved it, but be safe)
            if not keyring_get("device_token"):
                keyring_set("device_token", token)

            self._provision_worker = None

            # Show success UI
            self.dashboard_ui.update_loader("Device approved successfully")
            self.dashboard_ui.provision_overlay.set_state_success()
            
            # show toast
            self.dashboard_ui.show_overlay_feedback(
                "Device approved and credential received. Please login.",
                "success"
            )

            # Delay hiding overlay & opening login
            QTimer.singleShot(2500, lambda: (
                self.dashboard_ui.hide_loader(),
                self.open_login_window()
                )
            )

        except Exception as e:
            # Still proceed to login but inform user
            self.dashboard_ui.show_overlay_feedback(
                f"Provisioned but failed to persist token locally: {e}", 
                "info"
            )
            QTimer.singleShot(2500, self.open_login_window)

    
    def _on_provisioning_failure(self, message: str):
        """
        Provisioning thread signalled a failure status (e.g. rejected).
        Show message and leave retry/cancel visible.
        """
        self.dashboard_ui.update_loader(str(message))
        self.dashboard_ui.show_overlay_feedback(str(message), "error")
        self.dashboard_ui.provision_overlay.set_state_failed()
        # Keep worker reference cleared
        self._provision_worker = None


    def _on_credential_error(self, message: str):
        # Show final error and leave retry/cancel visible
        self.dashboard_ui.update_loader(f"Error: {message}")
        self.dashboard_ui.show_overlay_feedback(f"Error: {message}", "error")
        self.dashboard_ui.provision_overlay.set_state_failed()
        self._provision_worker = None

    
    # --------------- Login flow --------------
    def open_login_window(self):
        self.dashboard_ui.show_login_overlay()


    def handle_login_submission(self, username, password):
        """
        Called when operator logs in successfully.
        session_token is available for attendance calls.
        Show attendance page.
        """
        if not username or not password:
            self.dashboard_ui.show_overlay_feedback("Username and Password required", "error")
            return
        
        device_uuid = keyring_get("device_uuid")
        device_token = keyring_get("device_token")

        try:
            resp = self._api_client.operator_login(
                device_uuid=device_uuid,
                device_token=device_token,
                username=username,
                password=password
            )
        except Exception as e:
            message = str(e)
            # If API returned invalid credentials
            if "401" in message or "invalid" in message.lower():
                self.dashboard_ui.login_overlay.show_field_error_state("Invalid username or password")
                self.dashboard_ui.show_overlay_feedback("Invalid username or password", "error")
            else:
                # Real network/server failure
                self.dashboard_ui.login_overlay.show_field_error_state("Network or server error")
                self.dashboard_ui.show_overlay_feedback(str(e), "error")
            return
        
        session_token = resp.get("session_token")
        employee_id = resp.get("employee_id")
        operator_username = resp.get("username") or username

        if not session_token or not employee_id:
            self.dashboard_ui.login_overlay.show_field_error_state(
                "Invalid username or password"
            )
            return
        
        self._session_token = session_token
        self.dashboard_ui.login_overlay.show_success_state()

        QTimer.singleShot(400, lambda: 
            self.dashboard_ui.show_overlay_feedback(
                f"Login successful: Welcome {operator_username}", 
                "success"
            )
        )

        QTimer.singleShot(1800, self.dashboard_ui._hide_login_overlay)

        # Open attendance page
        self.dashboard_ui.content_stack.setCurrentIndex(self.page_attendance_idx)
        self.dashboard_ui.highlight_active_button(self.dashboard_ui.btn_attendance)