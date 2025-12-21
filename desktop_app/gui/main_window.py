# smart_attendance/gui/main_window.py
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from PyQt6.QtCore import QThreadPool
from functools import partial

from desktop_app.gui.attendance_window import AttendanceWindow
from desktop_app.gui.logs_window import LogsWindow
from desktop_app.gui.dashboard_ui import DashboardUI
from desktop_app.gui.login_window import LoginWindow
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
        self.dashboard_ui.set_loader_retry_callback(self._retry_provisioning_flow)
        self.dashboard_ui.set_loader_cancel_callback(self._cancel_provisioning_flow)

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
        self.dashboard_ui.show_waiting_controls(True)

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


    def _on_credential_fetched(self, token: str):
        """
        Called when provisioning thread successfully fetched token.
        Token may already be stored by the thread; ensure keyring has it.
        """
        try:
            # Ensure token present in keyring (thread should have saved it, but be safe)
            if not keyring_get("device_token"):
                keyring_set("device_token", token)

            # hide loader and controls
            self.dashboard_ui.show_waiting_controls(False)
            self.dashboard_ui.hide_loader()
            self._provision_worker = None

            # Notify user and open login window
            QMessageBox.information(self, "Device approved", "Device approved and credential received. Please login.")
            # proceed to login
            self.open_login_window()
        except Exception as e:
            # Still proceed to login but inform user
            QMessageBox.warning(self, "Warning", f"Provisioned but failed to persist token locally: {e}")
            self.open_login_window()

    
    def _on_provisioning_failure(self, message: str):
        """
        Provisioning thread signalled a failure status (e.g. rejected).
        Show message and leave retry/cancel visible.
        """
        self.dashboard_ui.update_loader(str(message))
        self.dashboard_ui.show_waiting_controls(True)
        # Keep worker reference cleared
        self._provision_worker = None


    def _on_credential_error(self, message: str):
        # Show final error and leave retry/cancel visible
        self.dashboard_ui.update_loader(f"Error: {message}")
        self.dashboard_ui.show_waiting_controls(True)
        self._provision_worker = None

    
    # --------------- Login flow --------------
    def open_login_window(self):
        """
        Opens LoginWindow. On successful operator login, the login window emits
        login_success(session_token, employee_id, username) which we listen for.
        """
        login = LoginWindow(api_client=self._api_client, parent=self)
        login.login_success.connect(self._on_operator_login_success)
        login.exec()


    def _on_operator_login_success(self, session_token: str, employee_id: int, username: str):
        """
        Called when operator logs in successfully.
        session_token is available for attendance calls.
        Show attendance page.
        """
        self._session_token = session_token
        # Hide any loader if present
        self.dashboard_ui.hide_loader()
        # Open attendance page
        self.dashboard_ui.content_stack.setCurrentIndex(self.page_attendance_idx)
        self.dashboard_ui.highlight_active_button(self.dashboard_ui.btn_attendance)
        QMessageBox.information(self, "Login successful", f"Welcome {username} (id={employee_id})")