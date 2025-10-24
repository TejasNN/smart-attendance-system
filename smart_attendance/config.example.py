import os
from services.shift_policy import ShiftPolicy

POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "username_here",
    "password": "password_here",
    "database": "attendance_db"
}

MONGO_CONFIG = {
    "host": "localhost",
    "port": 27017,
    "database": "attendance_log",
}

# Default office shift: 9:00 AM IST, 1-minute grace
DEFAULT_SHIFT_POLICY = ShiftPolicy(start_hour=9, start_minute=0, grace_minutes=1)

FACE_MATCH_TOLERANCE = 0.6
FACE_SKIP_INTERVAL = 3