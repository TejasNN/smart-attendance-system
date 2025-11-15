# smart_attendance/gui/main_window.py
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication
from PyQt6.QtCore import QTimer, QThreadPool
from functools import partial

from gui.attendance_window import AttendanceWindow
from gui.logs_window import LogsWindow
from gui.dashboard_ui import DashboardUI
from utils.utils import center_window
from threads.absentee_marker import AbsenteeWorker


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


    def on_registration_success(self):
        """Called when a new employee is registered successfully."""
        # Return to dashboard page after successfully registration
        self.dashboard_ui.content_stack.setCurrentIndex(0)
        self.dashboard_ui.highlight_active_button(self.dashboard_ui.btn_attendance)

        # Refresh attendance encodings
        if hasattr(self.attendance_page, "refresh_known_encodings"):
            self.attendance_page.refresh_known_encodings()