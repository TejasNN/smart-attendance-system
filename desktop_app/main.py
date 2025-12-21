# smart_attendance/main.py
import sys
from PyQt6.QtWidgets import QApplication
from desktop_app.gui.main_window import MainWindow
from desktop_app.database.postgres_db import PostgresDB
from desktop_app.database.mongo_db import MongoDB

def main():
    # PostgreSQL database setup
    post_db = PostgresDB()
    post_db.create_tables()

    # MongoDB database setup
    mongo_db = MongoDB()

    app = QApplication(sys.argv)
    window = MainWindow(post_db, mongo_db)
    window.show()
    exit_code = app.exec()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()