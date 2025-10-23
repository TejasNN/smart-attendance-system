from bson import ObjectId
from utils.utils import current_date_utc_midnight, current_datetime_utc
from services.shift_policy import ShiftPolicy

class AttendanceRecord:
    def __init__(self, employee_id: str, name: str, status: str, marked_by: str):
        self.employee_id = employee_id
        self.name = name
        self.date = current_date_utc_midnight()
        self.timestamp = current_datetime_utc()
        self.status = status.lower()
        self.marked_by = marked_by

        self.remarks = ShiftPolicy.get_remarks(self.timestamp) if self.status == "present" else self.status

    def to_dict(self):
        """
        Convert the record to a MongoDB-compatible dictionary.
        """
        return {
            "_id": ObjectId(),
            "employee_id": self.employee_id,
            "name": self.name,
            "date": self.date,
            "timestamp": self.timestamp,
            "status": self.status,
            "marked_by": self.marked_by,
            "remarks": self.remarks,
        }
        