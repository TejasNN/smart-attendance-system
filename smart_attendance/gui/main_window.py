# smart_attendance/gui/main_window.py
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import QTimer
from functools import partial

from gui.register_window import RegisterWindow
from gui.attendance_window import AttendanceWindow
from gui.logs_window import LogsWindow
from gui.dashboard_ui import DashboardUI
from utils.utils import center_window


class MainWindow(QMainWindow):
    def __init__(self, post_db, mongo_db, parent=None):
        super().__init__(parent)
        self.post_db = post_db
        self.mongo_db = mongo_db
        self.setWindowTitle("Smart Attendance System")
        self.setGeometry(200, 200, 1200, 700)
        center_window(self)

        # Integrate the new dashboard UI
        self.dashboard_ui = DashboardUI(logged_user="Admin")
        self.setCentralWidget(self.dashboard_ui)

        self.dashboard_ui.content_stack.setObjectName("contentStack")

        # add other windows into the dashboard's content stack so they render inside central frame
        # page 0 is the dashboard itself (already present). We'll add register, attendance, logs as pages.
        # Create instances but do NOT show as standalone windows; add them as widgets to stack.
        self.register_page = RegisterWindow(self.post_db)
        self.attendance_page = AttendanceWindow(self.post_db, self.mongo_db)
        self.logs_page = LogsWindow(self.mongo_db)

        # Add pages to the stack; store their page indexes
        self.dashboard_ui.content_stack.addWidget(self.register_page)
        self.page_register_idx = self.dashboard_ui.content_stack.indexOf(self.register_page)

        self.dashboard_ui.content_stack.addWidget(self.attendance_page)
        self.page_attendance_idx = self.dashboard_ui.content_stack.indexOf(self.attendance_page)

        self.dashboard_ui.content_stack.addWidget(self.logs_page)
        self.page_logs_idx = self.dashboard_ui.content_stack.indexOf(self.logs_page)

        # Wire up sidebar buttons
        self._connect_sidebar_buttons()

        self.dashboard_ui.content_stack.setCurrentIndex(0)
        self.dashboard_ui.highlight_active_button(self.dashboard_ui.btn_dashboard)
    
        # connect dashboard filter signal to handler that fetches data and updates UI
        self.dashboard_ui.date_filter_changed.connect(self.on_dashboard_filter_changed)

        # Trigger initial load
        QTimer.singleShot(300, lambda: self.on_dashboard_filter_changed("Today", None, None))

    def _connect_sidebar_buttons(self):
        btns = {
            self.dashboard_ui.btn_dashboard: 0,
            self.dashboard_ui.btn_register: self.page_register_idx,
            self.dashboard_ui.btn_attendance: self.page_attendance_idx,
            self.dashboard_ui.btn_logs: self.page_logs_idx,
        }
        for btn, idx in btns.items():
            try:
                btn.clicked.disconnect()
            except Exception:
                pass
            btn.clicked.connect(partial(self._switch_and_highlight, idx, btn))

        try:
            self.dashboard_ui.btn_absentees.clicked.disconnect()
        except Exception:
            pass
        self.dashboard_ui.btn_absentees.clicked.connect(lambda: print("Mark absentees - implement page"))

    # ----------------------------------------------------------------------
    def on_dashboard_filter_changed(self, filter_type, from_date, to_date):
        """
        This function updates dashboard metrics and charts
        whenever the date filter is changed.
        Replace dummy data fetch logic with real PostgreSQL/MongoDB queries later.
        """
        print(f"Dashboard filter changed: {filter_type}, {from_date}, {to_date}")

        # Example dummy data
        total_employees = 120
        present = 95
        absent = total_employees - present
        attendance_rate = round((present / total_employees) * 100, 2)
        today_late = 7
        avg_checkin = "09:32 AM"

        # Update metrics
        metrics = {
            "Total Employees": total_employees,
            "Present": present,
            "Absent": absent,
            "Attendance Rate": f"{attendance_rate}%",
            "Today Late": today_late,
            "Avg Check-in Time": avg_checkin
        }
        self.dashboard_ui.update_metrics(metrics)

        # Update charts
        self.dashboard_ui.update_pie(present, absent)
        categories = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        values = [90, 100, 95, 92, 97]
        self.dashboard_ui.update_bar(categories, values)

    def _switch_and_highlight(self, page_idx, button):
        self.dashboard_ui.content_stack.setCurrentIndex(page_idx)
        self.dashboard_ui.highlight_active_button(button)