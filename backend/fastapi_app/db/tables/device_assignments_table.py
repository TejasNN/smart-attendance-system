# backend/fastapi_app/db/tables/device_assignments_table.py
def create_device_assignments_table(cursor):
    query = """
    CREATE TABLE IF NOT EXISTS device_assignments (
      id SERIAL PRIMARY KEY,
      device_id INTEGER REFERENCES devices(device_id) ON DELETE CASCADE,
      employee_id INTEGER REFERENCES users(employee_id) ON DELETE CASCADE,
      assigned_by INTEGER REFERENCES users(employee_id),
      assigned_at TIMESTAMPTZ DEFAULT now(),
      UNIQUE(device_id, employee_id)
    );
    """
    cursor.execute(query)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_assignments_device ON device_assignments (device_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_assignments_employee ON device_assignments (employee_id);")
