# backend/app/db/repos/user_repo.py
from typing import Optional, Dict, Any
from backend.fastapi_app.db.postgres_db import PostgresDB

class UserRepository:
    def __init__(self):
        self._db = PostgresDB()

    
    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT u.employee_id, u.username, u.password_hash, u.role, u.is_active, e.name AS employee_name
            FROM users u
            LEFT JOIN employees e ON e.employee_id = u.employee_id
            WHERE u.username = %s
            LIMIT 1;
        """
        try:
            self._db.cursor.execute(query, (username,))
            return self._db.cursor.fetchone()
        except Exception:
            return None
        
    
    def close(self):
        try:
            self._db.close()
        except Exception:
            pass
