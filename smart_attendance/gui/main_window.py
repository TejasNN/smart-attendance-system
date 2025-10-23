# smart_attendance/gui/main_window.py
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication
from PyQt6.QtCore import QTimer, QThreadPool
from functools import partial

from gui.register_window import RegisterWindow
from gui.attendance_window import AttendanceWindow
from gui.logs_window import LogsWindow
from gui.dashboard_ui import DashboardUI
from utils.utils import center_window
from threads.absentee_marker import AbsenteeWorker

MIN_LOADER_MS = 2500    # minimum miliseconds the loader should remain visible

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

        # threadpool for background tasks
        self.thread_pool = QThreadPool.globalInstance()

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
        self.dashboard_ui.btn_absentees.clicked.connect(self.start_mark_absentees)

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

    def start_mark_absentees(self):
        """
        Called when user clicks Mark Absentees on dashboard.
        Shows loader and starts AbsenteeWorker in threadpool.
        Ensures loader is visible at least MIN_LOADER_MS for UX.
        """
        # --- Ensure we are on the dashboard window ---
        dashboard_index = 0
        current_index = self.dashboard_ui.content_stack.currentIndex()

        if current_index != dashboard_index:
            # Smoothly switch to dashboard page before starting
            direction = "right" if current_index > dashboard_index else "left"
            self.dashboard_ui.animate_page_transition(current_index, dashboard_index, direction)

            # Add small delay for visual smoothness
            QTimer.singleShot(450, self.start_mark_absentees)
            return
        
        # --- Proceed only if we are already on the Dashboard ---
        # Disable the mark absentee button to prevent mutiple clicks
        self.dashboard_ui.btn_absentees.setEnabled(False)

        # Show loader in dashboard with an initial message
        self.dashboard_ui.show_loader("Starting absentee marking...")

        # record when loader was shown (ms)
        self._loader_shown_time = QTimer().remainingTime()  # dummy to ensure attribute exists
        import time
        self._loader_start_ts = int(time.time() * 1000)

        worker = AbsenteeWorker(self.post_db, self.mongo_db, marked_by="Admin")

        # Connect signals
        worker.signals.step.connect(self.dashboard_ui.update_loader)
        # optional: update progress percent: not used here as we don't show percent
        worker.signals.progress.connect(lambda p : None)

        def on_done(summary):
            # Called in main thread when worker finishes.
            # Ensure minimum loader display time
            elapsed = int(time.time() * 1000) - self._loader_start_ts
            remaining = max(0, MIN_LOADER_MS - elapsed)

            def finish(): 
                # hide loader, show summary and refresh dashboard + logs
                self.dashboard_ui._pending_summary = summary

                # Queue a final message for smooth closure
                self.dashboard_ui.update_loader("Saving absentee records to database...")
                
                # Refresh data in background after summary appears
                QTimer.singleShot(2000, lambda: self.on_dashboard_filter_changed(
                    self.dashboard_ui.filter_combo.currentText(), None, None
                ))
                
                # Refresh logs
                QTimer.singleShot(2000, lambda: self.logs_page.load_logs())
                
            
            QTimer.singleShot(remaining, finish)

        def on_error(error):
            # hide loader immediately and show error
            self.dashboard_ui.hide_loader()
            QMessageBox.critical(self, "Error", f"Absentee worker failed:\n{error}")

        worker.signals.done.connect(on_done)
        worker.signals.error.connect(on_error)

        # Start worker
        self.thread_pool.start(worker)