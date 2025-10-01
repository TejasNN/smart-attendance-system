from pymongo import MongoClient
from datetime import datetime
from config import MONGO_CONFIG

class MongoDB:
    def __init__(self):
        self.client = MongoClient(MONGO_CONFIG['host'], MONGO_CONFIG['port'])
        self.db = self.client[MONGO_CONFIG['database']]
        self.collection = self.db['logs']

        # Add indexes for date and employee_id
        self.collection.create_index("date")
        self.collection.create_index("employee_id")

    def log_attendance(self, record: dict):
        self.collection.insert_one(record)
        return True

    def get_logs(self):
        return list(self.collection.find())
    
    def check_valid_entry_for_date(self, employee_id):
        # Prevents duplicate entries for same employee_id on same date
        today = datetime.today().strftime("%Y-%m-%d")
        exists = self.collection.find_one({
            "employee_id": employee_id,
            "date": today
        })
        if exists:
            return True    # Already Marked