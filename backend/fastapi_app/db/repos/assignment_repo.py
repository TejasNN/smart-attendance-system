# backend/fastapi_app/db/repos/assignment_repo.py
from typing import Optional
from backend.fastapi_app.db.postgres_db import PostgresDB

class AssignmentRepository:
    def __init__(self):
        self._db = PostgresDB()


    def is_user_assigned_to_device(self, employee_id: int, device_id: int) -> bool:
        query = """
            SELECT 1 FROM device_assignments WHERE employee_id = %s AND device_id = %s LIMIT 1;
        """
        try:
            self._db.cursor.execute(query, (employee_id, device_id))
            return self._db.cursor.fetchone()
        except Exception:
            return False
        
    
    def close(self):
        try:
            self._db.close()
        except Exception:
            pass