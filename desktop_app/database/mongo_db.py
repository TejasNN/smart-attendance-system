from pymongo import MongoClient, ASCENDING
from datetime import datetime, timezone, time
from desktop_app.utils.utils import current_date_utc_midnight
from desktop_app.config import MONGO_CONFIG

class MongoDB:
    def __init__(self):
        self.client = MongoClient(MONGO_CONFIG['host'], MONGO_CONFIG['port'])
        self.db = self.client[MONGO_CONFIG['database']]
        self.collection = self.db['logs']

        # Add indexes for date and employee_id
        # Compound unique index to prevent duplocate employee/day entries
        self.collection.create_index([("employee.id", ASCENDING), ("attendance.date", ASCENDING)], unique=True)
        self.collection.create_index("attendance.date")
        self.collection.create_index("employee.id")
        

    def log_attendance(self, record: dict):
        """
        Insert a single record. If duplicate on (employee_id,date) it'll raise a DuplicateKeyError.
        Caller can handle exceptions if they want to skip duplicates.
        """
        self.collection.insert_one(record)
        return True

    def get_logs(self):
        return list(self.collection.find())
    
    
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

        exists = self.collection.find_one({
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

        present_docs = self.collection.find(
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
            result = self.collection.insert_many(records, ordered=False)
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
        