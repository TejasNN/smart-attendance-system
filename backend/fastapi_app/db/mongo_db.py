# backend/fastapi_app/db/mongo_db.py
from pymongo import MongoClient, ASCENDING
from datetime import datetime, timezone, time
from desktop_app.utils.utils import current_date_utc_midnight, current_datetime_utc
from desktop_app.config import MONGO_CONFIG
from backend.fastapi_app.schemas.provisioning import DeviceLogDTO
from typing import Optional, List, Dict, Any

class MongoDB:
    def __init__(self):
        self.client = MongoClient(MONGO_CONFIG['host'], MONGO_CONFIG['port'])
        self.db = self.client[MONGO_CONFIG['database']]

        # existing attendance logs collection (kept for backwards compatibility)
        self.attendance = self.db['logs']
        self.attendance.create_index([("employee.id", ASCENDING), ("attendance.date", ASCENDING)], unique=True)
        self.attendance.create_index("attendance.date")
        self.attendance.create_index("employee.id")

        # device_logs (events from devices)
        self.device_logs = self.db['device_logs']
        self.device_logs.create_index([("device.id", ASCENDING), ("timestamp", ASCENDING)])
        self.device_logs.create_index("timestamp")

        # user_login_logs (operator login attempts/events)
        self.user_login_logs = self.db['user_login_logs']
        self.user_login_logs.create_index([("user.id", ASCENDING), ("timestamp", ASCENDING)])
        self.user_login_logs.create_index("timestamp")

    # ----------------------------
    # Attendance helpers (existing)
    # ----------------------------

    def log_attendance(self, record: dict):
        self.attendance.insert_one(record)
        return True
    

    def get_logs(self):
        return list(self.attendance.find())
    

    def check_valid_entry_for_date(self, employee_id, date_obj=None):
        """
        Returns True if an attendance record exists for the given employee_id and UTC date.
        If date_obj is None, today's UTC midnight date is used.
        """
        if date_obj is None:
            today_utc = current_date_utc_midnight()
        elif isinstance(date_obj, str):
            # Convert 'YYYY-MM-DD' string to datetime at midnight IST
            date_dt = datetime.fromisoformat(date_obj)
            today_utc = datetime.combine(date_dt.date(), time(0, 0, 0, tzinfo=timezone.utc))
        elif isinstance(date_obj, datetime):
            # Normalize datetime to midnight UTC
            today_utc = datetime.combine(date_obj.astimezone(timezone.utc).date(), time(0,0,0, tzinfo=timezone.utc))
        else:
            raise TypeError("date_obj must be None, str, or datetime")

        exists = self.attendance.find_one({
            "employee.id": employee_id,
            "attendance.date": today_utc
        })
        return bool(exists)
    

    def get_present_employee_ids(self) -> list[str]:
        """
        Returns a list of employee_ids marked 'present' for today's IST date.
        Uses IST date at midnight for consistent querying.
        """
        today_utc = current_date_utc_midnight()

        present_docs = self.attendance.find(
            {"attendance.date": today_utc, "attendance.status": "present"},
            {"employee.id": 1, "_id": 0}
        )
        return [str(doc["employee"]["id"]) for doc in present_docs]
    

    def insert_absentees_bulk(self, records: list[dict]) -> dict:
        """
        Insert a list of attendance dicts. Uses ordered=False so the insert continues if duplicates found,
        and returns a summary dict with inserted_count and errors.
        We assume records are already properly shaped (with date as datetime, timestamp as datetime, etc.)
        """
        if not records:
            return {"inserted": 0, "skipped": 0, "errors": []}

        try:
            result = self.attendance.insert_many(records, ordered=False)
            inserted = len(result.inserted_ids)
            return {"inserted": inserted, "skipped": 0, "errors": []}
        except Exception as e:
            # If duplicates are attempted (unique index), insert_many raises BulkWriteError.
            # We will analyze writeErrors to compute inserted vs skipped.
            from pymongo.errors import BulkWriteError
            if isinstance(e, BulkWriteError):
                details = e.details
                write_errors = details.get("writeErrors", [])
                # count duplicated vs other
                dup_count = sum(1 for we in write_errors if we.get("code") == 11000)
                inserted = details.get("nInserted", 0)
                other_errors = [we for we in write_errors if we.get("code") != 11000]
                return {"inserted": inserted, "skipped": dup_count, "errors": other_errors}
            else:
                return {"inserted": 0, "skipped": 0, "errors": [str(e)]}
            
    # ----------------------------
    # Device logging (new)
    # ----------------------------

    def log_device_event(self, device_id:int, device_uuid: str, user_id:int, event_type: str, details: dict) -> bool:
        dto = DeviceLogDTO(
            device_id=device_id,
            device_uuid=device_uuid,
            user_id=user_id,
            event_type=event_type,
            details=details,
            timestamp= current_datetime_utc()
        )
        self.device_logs.insert_one(dto.to_mongo())
        return True
    

    def get_device_logs(self, device_id: int, limit: int= 100) -> List[Dict[str, Any]]:
        """
        Fetches recent device logs for a device, sorted by timestamp (desc),
        and removes MongoDB internal fields like `_id` before returning.
        """
        cursor = self.device_logs.find({"device.id": device_id}).sort("timestamp", -1).limit(limit)
        logs = []

        for doc in cursor:
            doc = self.sanitize_mongo_doc(doc)
            logs.append(doc)
            
        return logs
    

    def log_user_login(self, user_id: int, username: str, device_id: Optional[int], 
                       device_uuid: Optional[str], outcome: str, meta: dict=None) -> bool:
        doc = {
            "user": {
                "id": user_id,
                "username": username
            },
            "device": {
                "id": device_id,
                "uuid": device_uuid
            },
            "outcome": outcome,
            "meta": meta or {},
            "timestamp": current_datetime_utc()
        }
        self.user_login_logs.insert_one(doc)
        return True
    

    def get_user_login_logs(self, user_id: int, limit: int=100):
        cursor = self.user_login_logs.find({"user.id": user_id}).sort("timestamp", -1).limit(limit)
        return list(cursor)
    

    def sanitize_mongo_doc(doc):
        if "_id" in doc:
            del doc["_id"]
        return doc