import os
import calendar
from datetime import datetime, timedelta
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QWidget

def reset_fields(self) -> None:
    # Remove temp photo if exists
    if self.photo_path and os.path.exists(self.photo_path):
        try:
            os.remove(self.photo_path)
        except Exception as e:
            print(f"Could not remove temp file {self.photo_path}: {e}")

    self.name_input.clear()
    self.dept_input.setCurrentIndex(0)
    self.photo_path = None

def center_window(window: QWidget) -> None:
    screen = QGuiApplication.primaryScreen().availableGeometry()
    frame = window.frameGeometry()
    frame.moveCenter(screen.center())
    window.move(frame.topLeft())

def get_week_range(today: datetime, week_offset=0):
    """Return Monday and Saturday for the week of the given date."""
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    saturday = monday + timedelta(days=5)
    return monday, saturday

def get_filename_wrt_date_filter_and_searchbox(filter_option, search_text):
    # Filename wrt filter selection
    today = datetime.today()
    default_filename = "_log"
    if filter_option == "Today":
        filename = f"{today.strftime('%d-%b-%Y')}_{default_filename}"
    elif filter_option == "This Week":
        monday, saturday =  get_week_range(today)
        filename =f"{monday.strftime('%d-%b-%Y')}_{saturday.strftime('%d-%b-%Y')}{default_filename}"
    elif filter_option == "This Month":
        month_abbr_name = calendar.month_abbr[today.month]
        filename = f"{month_abbr_name}_{today.year}{default_filename}"

    # prepend search text if available
    if search_text.strip():
        # Clean spaces and special character for safety
        safe_text = "_".join(search_text.strip().split())
        filename = f"{safe_text}_{filename}"
    return filename