# backend/fastapi_app/db/repos/assignment_repo.py
import logging
from typing import Optional, List, Dict, Any
from backend.fastapi_app.db.postgres_db import PostgresDB

logger = logging.getLogger(__name__)


class AssignmentRepository:
    def __init__(self):
        self._db = PostgresDB()


    def is_user_assigned_to_device(self, employee_id: int, device_id: int) -> bool:
        try:
            return self._db.is_employee_assigned_to_device(device_id, employee_id) 
        except Exception as e:
            logger.exception(f"Check assingment failed: {e}")
            raise
        
    
    def assign_users_to_device(self, device_id: int, employee_id: List[int], assigned_by: Optional[int] = None) -> int:
        """
        Insert multiple employee assignments for the device.
        Uses ON CONFLICT DO NOTHING to avoid duplicate errors.
        Returns the number of rows actually inserted.
        """
        inserted = 0
        try:
            for emp in employee_id:
                try:
                    row = self._db.assign_employee_to_device(device_id, emp, assigned_by)
                    if row:
                        inserted += 1
                except Exception as e:
                    logger.warning(f"Failed to insert assignment for employee = {emp}: {e}")
                    self._db.conn.rollback()
                    continue
            return inserted
        
        except Exception as e:
            logger.exception(f"Bulk assingment failed: {e}")
            self._db.conn.rollback()
            raise
    

    def get_assignments_for_device(self, device_id) -> List[Dict[str, Any]]:
        try:
            return self._db.get_assignments_for_device(device_id) or []
        except Exception as e:
            logger.exception(f"Failed to load device assignments: {e}")
            raise
        

    def validate_employees(self, employee_ids: List[int]) -> List[int]:
        """
        Return subset of employee_ids that actually exist in users.employee_id
        """
        if not employee_ids:
            return []
        
        try:
            rows = self._db.validate_employee_ids(employee_ids)
            return [r['employee_id'] for r in rows] if rows else []
        except Exception as e:
            logger.exception(f"Failed validating employees: {e}")
            raise


    def remove_assignments(self, device_id: int) -> bool:
        try:
            self._db.remove_assignments_for_device(device_id)
            return True
        except Exception as e:
            logger.exception(f"Failed removing assignments: {e}")
            raise
