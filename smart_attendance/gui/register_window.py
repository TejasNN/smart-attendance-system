# register_window.py
import os
import cv2
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox
from PyQt6.QtCore import pyqtSignal
from utils.utils import center_window, reset_fields
from services.photo_storage import PhotoStorage
from services.face_recognizer import FaceRecongnizer

class RegisterWindow(QWidget):
    registration_successful = pyqtSignal()
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.photo_path = None
        self.setWindowTitle("Employee Registration")
        self.setGeometry(300, 300, 200, 250)
        center_window(self)

        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        self.dept_input = QComboBox()
        self.dept_input.setPlaceholderText("---Select Dept---")
        self.dept_input.addItems(["HR", "IT", "Sales", "Admin"])

        self.btn_capture = QPushButton("Capture")
        self.btn_save = QPushButton("Save")

        layout.addWidget(QLabel("Name"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Department"))
        layout.addWidget(self.dept_input)
        layout.addWidget(self.btn_capture)
        layout.addWidget(self.btn_save)

        self.setLayout(layout)

        # Services
        self.photo_storage = PhotoStorage()
        self.face_recognizer = FaceRecongnizer()

        # Event bindings
        self.btn_capture.clicked.connect(self.capture_photo)
        self.btn_save.clicked.connect(self.save_employee)

    def capture_photo(self) -> None:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            QMessageBox.critical(self, "Error", "Could not access camera.")
            return
        
        QMessageBox.information(self, "Info", "Press 'SPACE' to capture photo, 'ESC' to cancel.")

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                QMessageBox.critical(self, "Error", "Failed to capture image.")
                break

            cv2.imshow("Capture Photo - Press SPACE to capture", frame)

            key = cv2.waitKey(1)

            if key == 27:  # ESC key
                break

            elif key == 32:  # SPACE key
                # save temporary photo
                self.photo_path = self.photo_storage.save_temp_photo(frame)

                # Extract face encoding
                face_encoding, _ = self.face_recognizer.extract_face_encoding(frame)
                if not face_encoding:
                    QMessageBox.warning(self, "Warning", "No face detected. Please try again.")
                    self.photo_path = None
                else:
                    self.face_encoding = face_encoding[0]
                    QMessageBox.information(self, "Info", f"Photo captured successfully")
                break

        cap.release()
        cv2.destroyAllWindows()

    def save_employee(self) -> None:
        name = self.name_input.text().strip()
        department = self.dept_input.currentText()

        # Validation for empty fields
        if not name or department == "---Select Dept---" or not self.photo_path:
            QMessageBox.warning(self, "Warning", "Please fill/select all fields and capture a photo.")
            return
        
        # Step 1: Save employee in DB (without photo)
        emp_id = self.db.add_employee(name, department, self.face_encoding.tolist())

        # Step 2: Move photo to permanant location
        final_photo_path = self.photo_storage.move_to_employee_folder(emp_id, self.photo_path)

        # Step 4: Update DB with photo path
        self.db.update_photo_path(emp_id, final_photo_path)
        QMessageBox.information(self, "Saved", f"Employee registered with ID: {emp_id}")
        
        # Step 5: Reset all fields
        reset_fields(self)

        # Step 6: Send registration complete signal
        self.registration_successful.emit()

# The above code defines a RegisterWindow class for registering employees with photo capture functionality.