import psycopg2
from psycopg2.extras import RealDictCursor
from config import POSTGRES_CONFIG
import pickle   # for serializing face encodings

class PostgresDB:
    def __init__(self):
        self.conn = psycopg2.connect(**POSTGRES_CONFIG)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)

    def create_tables(self):
        query = """ 
                    CREATE TABLE IF NOT EXISTS employees 
                    (   employee_id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        department VARCHAR(50) NOT NULL,
                        photo_path TEXT,
                        face_encoding BYTEA
                    );
            """
        self.cursor.execute(query)
        self.conn.commit()

    def add_employee(self, name, department, face_encoding):
        query = """
                    INSERT INTO employees (name, department, face_encoding) 
                    VALUES (%s, %s, %s) 
                    RETURNING employee_id;
            """
        face_encoding_binary = pickle.dumps(face_encoding)
        self.cursor.execute(query, (name, department, face_encoding_binary))                    
        emp_id = self.cursor.fetchone()['employee_id']
        self.conn.commit()
        return emp_id

    def update_photo_path(self, employee_id, photo_path):
        query = """
            update employees
            SET photo_path = %s
            WHERE employee_id = %s;
        """
        self.cursor.execute(query, (photo_path, employee_id))
        self.conn.commit()
    
    def get_all_employees(self):
        self.cursor.execute("SELECT * FROM employees")
        return self.cursor.fetchall()
    
    def get_employee_by_id(self, employee_id: int):
        query = """
            SELECT employee_id, name, department, photo_path 
            FROM employees
            WHERE employee_id = %s;
        """
        self.cursor.execute(query, (employee_id,))
        return self.cursor.fetchone()
    
    def get_all_encodings(self):
        """
        Returns a list of dicts: [{'employee_id': id, 'name': name, 'department': dept, 'face_encoding': np.ndarray}, ...]
        Decodes the pickled face_encoding stored in the face_encoding BYTEA column.
        """
        self.cursor.execute("SELECT employee_id, name, department, face_encoding FROM employees WHERE face_encoding IS NOT NULL")
        rows = self.cursor.fetchall()
        results = []
        for r in rows:
            face_encoding_bytes = r.get('face_encoding')
            if not face_encoding_bytes:
                continue
            
            encoding = pickle.loads(face_encoding_bytes)     # this yields numpy array saved previously

            results.append({
                "employee_id": r["employee_id"],
                "name": r["name"],
                "department": r["department"],
                "face_encoding": encoding,
            })
        return results