# backend/fastapi_app/db/postgres_db.py
from psycopg2.extras import RealDictCursor, Json
from typing import Optional, List, Dict, Any
from .connection import get_pg_connection
from .tables.users_table import create_users_table
from .tables.devices_table import create_devices_table
from .tables.device_assignments_table import create_device_assignments_table
import psycopg2

class PostgresDB:
    def __init__(self):
        # Each instance opens its own connection
        self.conn = get_pg_connection()
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)

    def close(self):
        try:
            self.cursor.close()
        except Exception:
            pass
        try:
            self.conn.close()
        except Exception:
            pass

    def create_all_tables(self):
        """
        Orchestrator to create all tables.
        """
        create_users_table(self.cursor)
        create_devices_table(self.cursor)
        create_device_assignments_table(self.cursor)
        self.conn.commit()

    # ----------------------------
    # Devices helpers
    # ----------------------------

    def add_device_registration(self, device_uuid: str, device_name: Optional[str]=None,
                                assigned_site: Optional[str]=None, app_version: Optional[str]=None,
                                os_version: Optional[str]=None, registered_by: Optional[int]=None) -> Optional[int]:
        """
        Insert a register-request row (status = pending). Returns device_id.
        device_name, assigned_site, app_version, os_version are optional metadata from the PyQt client.
        """
        query = """
        INSERT INTO devices (device_uuid, device_name, assigned_site, app_version, os_version, 
        registered_by, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, 'pending', now(), now())
        RETURNING device_id;
        """
        self.cursor.execute(query, (device_uuid, device_name, assigned_site, app_version, os_version, registered_by))
        row = self.cursor.fetchone()
        self.conn.commit()
        return row['device_id'] if row else None
    
    
    def get_device_by_uuid(self, device_uuid: str) -> Optional[Dict]:
        query = "SELECT * FROM devices WHERE device_uuid = %s;"
        self.cursor.execute(query, (device_uuid,))
        return self.cursor.fetchone()
    

    def get_device_by_id(self, device_id: int) -> Optional[Dict]:
        query = "SELECT * FROM devices WHERE device_id = %s;"
        self.cursor.execute(query, (device_id,))
        return self.cursor.fetchone()
    
    
    def set_device_credential(self, device_id: int, credential_hash: str, status: str='active', 
                              device_name: Optional[str]=None, app_version: Optional[str]=None,
                              os_version: Optional[str]=None):
        query = """
        UPDATE devices
        SET credential_hash = %s,
            status = %s,
            device_name = COALESCE(%s, device_name),
            app_version = COALESCE(%s, app_version),
            os_version = COALESCE(%s, os_version),
            updated_at = now()
        WHERE device_id = %s;
        """
        self.cursor.execute(query, (credential_hash, status, device_name, app_version, os_version,device_id))
        self.conn.commit()


    def get_pending_devices(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Return devices with status = 'pending', ordered by created_at desc.
        """
        query = """
            SELECT device_id, device_uuid, device_name, assigned_site, app_version, 
            os_version, status, created_at
            FROM devices
            WHERE status = 'pending'
            ORDER BY created_at DESC
            LIMIT %s;
        """
        self.cursor.execute(query, (limit,))
        rows = self.cursor.fetchall()
        return rows
    

    def get_all_devices(self, limit: int = 100):
        query = """
            SELECT device_id, device_uuid, device_name, status, assigned_site, 
            app_version, os_version, last_update_check, created_at
            FROM devices
            ORDER BY created_at DESC
            LIMIT %s;
        """
        self.cursor.execute(query, (limit,))
        rows = self.cursor.fetchall()
        return rows
    

    def clear_token(self, device_id: int) -> None:
        """
        Set credential_hash to NULL so device must fetch a new token after approval.
        """
        query = """
            UPDATE devices
            SET credential_hash = NULL, updated_at = now()
            WHERE device_id = %s;
        """
        self.cursor.execute(query, (device_id,))
        self.conn.commit()
         

    def update_device_status(self, device_id: int, status: str):
        query = "UPDATE devices SET status = %s, updated_at = now() WHERE device_id = %s;"
        self.cursor.execute(query, (status, device_id))
        self.conn.commit()

    
    def touch_device_update_check(self, device_id: int):
        query = "UPDATE devices SET last_update_check = now(), updated_at = now() WHERE device_id = %s;"
        self.cursor.execute(query, (device_id,))
        self.conn.commit()

    # ----------------------------
    # Device assignment helpers
    # ----------------------------
    
    def assign_employee_to_device(self, device_id: int, employee_id: int, assigned_by: Optional[int]=None) -> bool:
        query = """
        INSERT INTO device_assignments (device_id, employee_id, assigned_by)
        VALUES (%s, %s, %s)
        ON CONFLICT (device_id, employee_id) DO NOTHING
        RETURNING id; 
        """
        self.cursor.execute(query, (device_id, employee_id, assigned_by))
        row = self.cursor.fetchone()
        self.conn.commit()
        return bool(row)
    
    
    def get_assigned_employees(self, device_id: int) -> List[Dict]:
        query = """
        SELECT da.id, da.device_id, da.employee_id, u.username, da.assigned_at
        FROM device_assignments da
        JOIN users u ON u.employee_id = da.employee_id
        WHERE da.device_id = %s;
        """
        self.cursor.execute(query, (device_id,))
        return self.cursor.fetchall()
    

    def get_assignments_for_device(self, device_id: int) -> List[Dict[str, Any]]:
        query = """
        SELECT da.id, da.device_id, da.employee_id, u.username, da.assigned_at
        FROM device_assignments da
        LEFT JOIN users u ON u.employee_id = da.employee_id
        WHERE da.device_id = %s
        ORDER BY da.assigned_at DESC;
        """
        self.cursor.execute(query, (device_id,))
        return self.cursor.fetchall()
    

    def remove_assignments_for_device(self, device_id: int) -> None:
        """
        Remove ALL assignments for the given device.
        Used when device is revoked/deactivated by admin.
        """
        query = """
            DELETE FROM device_assignments
            WHERE device_id = %s;
        """
        self.cursor.execute(query, (device_id,))
        self.conn.commit()
    
    def is_employee_assigned_to_device(self, device_id: int, employee_id: int) -> bool:
        query = "SELECT 1 FROM device_assignments WHERE device_id = %s AND employee_id = %s;"
        self.cursor.execute(query, (device_id, employee_id))
        return bool(self.cursor.fetchone())
    
    # ----------------------------
    # Users helpers (minimal)
    # ----------------------------

    def create_user(self, employee_id: int, username: str, password_hash: str, role: str='operator', is_active: bool=True):
        query = """
        INSERT INTO users (employee_id, username, password_hash, role, is_active, created_at)
        VALUES (%s, %s, %s, %s, %s, now())
        RETURNING employee_id;
        """
        self.cursor.execute(query, (employee_id, username, password_hash, role, is_active))
        row = self.cursor.fetchone()
        self.conn.commit()
        return row['employee_id'] if row else None
    

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        query = "SELECT * FROM users WHERE username = %s;"
        self.cursor.execute(query, (username,))
        return self.cursor.fetchone()
    

    def validate_employee_ids(self, employee_ids: List[int]) -> List[int]:
        query = """
            SELECT employee_id
            FROM users
            WHERE employee_id = ANY(%s);
        """
        self.cursor.execute(query, (employee_ids,))
        rows = self.cursor.fetchall()
        return rows
    

    def get_user_status(self, employee_id: int) -> Optional[Dict]:
        query = """
            SELECT username, is_active 
            FROM users 
            WHERE employee_id = %s 
            LIMIT 1;
        """
        self.cursor.execute(query, (employee_id,))
        return self.cursor.fetchone()