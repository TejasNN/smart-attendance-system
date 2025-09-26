import os

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

FACE_MATCH_TOLERANCE = 0.6