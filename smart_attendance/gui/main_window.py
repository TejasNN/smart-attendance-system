# smart_attendance/gui/main_window.py
from PyQt6.QtWidgets import QMainWindow, QApplication, QVBoxLayout, QWidget, QPushButton
from gui.register_window import RegisterWindow
from gui.attendance_window import AttendanceWindow
from gui.logs_window import LogsWindow
from utils.utils import center_window

class MainWindow(QMainWindow):
    def __init__(self, post_db, mongo_db, parent=None):
        super().__init__(parent)
        self.post_db = post_db
        self.mongo_db = mongo_db
        self.setWindowTitle("Smart Attendance System")
        self.setGeometry(200, 200, 400, 300)
        center_window(self)

        layout = QVBoxLayout()
        
        self.btn_register = QPushButton("Register Employee")
        self.btn_attendance = QPushButton("Mark Attendance")
        self.btn_logs = QPushButton("View attendance Logs")
        
        layout.addWidget(self.btn_register)
        layout.addWidget(self.btn_attendance)
        layout.addWidget(self.btn_logs)
        
        container = QWidget()
        container.setLayout(layout)
        
        self.setCentralWidget(container)
        
        # Connect buttons to their respective methods
        self.btn_register.clicked.connect(self.open_register)
        self.btn_attendance.clicked.connect(self.open_attendance)
        self.btn_logs.clicked.connect(self.open_logs)

    def open_register(self):
        self.register_window = RegisterWindow(self.post_db)
        self.register_window.show()

    def open_attendance(self):
        self.attendance_window = AttendanceWindow(self.post_db, self.mongo_db)
        self.attendance_window.show()

    def open_logs(self):
        self.logs_window = LogsWindow(self.mongo_db)
        self.logs_window.show()