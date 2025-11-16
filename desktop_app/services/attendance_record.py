from bson import ObjectId
from utils.utils import current_date_utc_midnight, current_datetime_utc
from config import DEFAULT_SHIFT_POLICY

class AttendanceRecord:
    def __init__(self, employee_id: str, name: str, department: str, status: str, marked_by: str):
        self.employee_id = employee_id
        self.name = name
        self.department = department
        self.date = current_date_utc_midnight()
        self.timestamp = current_datetime_utc()
        self.status = status.lower()
        self.marked_by = marked_by

        self.remarks = DEFAULT_SHIFT_POLICY.get_remarks(self.timestamp) if self.status == "present" else self.status

    def to_dict(self):
        """
        Convert the record to a MongoDB-compatible dictionary.
        """
        return {
            "_id": ObjectId(),
            "employee": {
                "id": self.employee_id,
                "name": self.name,
                "department": self.department,
            },
            "attendance": {
                "date": self.date,
                "status": self.status,
                "remarks": self.remarks,
                "marked_by": self.marked_by, 
            },
            "timestamp": self.timestamp,
        }
        