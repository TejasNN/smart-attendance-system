# backend/fastapi_app/db/tables/users_table.py
def create_users_table(cursor):
    query = """
    CREATE TABLE IF NOT EXISTS users (
        employee_id INTEGER PRIMARY KEY REFERENCES employees(employee_id) ON DELETE CASCADE,
        username VARCHAR(100) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role VARCHAR(20) NOT NULL CHECK (role IN ('admin','operator')),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT now()
    );
    """
    cursor.execute(query)