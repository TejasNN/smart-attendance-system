# smart_attendance/main.py
import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow
from database.postgres_db import PostgresDB
from database.mongo_db import MongoDB
from utils.absentee_scheduler import SchedulerManager

def main():
    # PostgreSQL database setup
    post_db = PostgresDB()
    post_db.create_tables()

    # MongoDB database setup
    mongo_db = MongoDB()

    # Initialize auto absentee marking scheduler
    scheduler = SchedulerManager()
    scheduler.start()

    app = QApplication(sys.argv)
    window = MainWindow(post_db, mongo_db)
    window.show()
    exit_code = app.exec()
    scheduler.shutdown()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()