import os
import calendar
import pytz
from datetime import datetime, timedelta, timezone, time
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QWidget

IST = pytz.timezone("Asia/Kolkata")

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

def current_datetime_utc() -> datetime:
    """Return current utc datetime (timezone-aware)."""
    return datetime.now(timezone.utc)

def current_date_utc_midnight() -> datetime:
    """Return UTC date at midnight (00:00:00)."""
    now_utc = current_datetime_utc()
    midnight_utc = datetime.combine(now_utc.date(), time(0, 0, 0, tzinfo=timezone.utc))
    return midnight_utc

def _ensure_utc_aware(dt: datetime) -> datetime:
    """Return tz-aware datetime in UTC. If dt is naive, treat it as UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def get_ist_time_from_utc(utc_time: datetime) -> str:
    """Convert a UTC datetime to IST formatted string."""
    if not utc_time:
        return ""
    utc_aware = _ensure_utc_aware(utc_time)
    ist_time = utc_aware.astimezone(IST).strftime("%d-%m-%Y %H:%M:%S")
    return ist_time

def get_ist_date_from_utc(utc_date: datetime) -> str:
    """Convert a UTC date to IST formatted string."""
    if not utc_date:
        return None
    utc_aware = _ensure_utc_aware(utc_date)
    ist_date = utc_aware.astimezone(IST).strftime("%d-%m-%Y")
    return ist_date
