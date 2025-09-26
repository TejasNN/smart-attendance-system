import cv2
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
from services.face_recognizer import FaceRecongnizer
from config import FACE_MATCH_TOLERANCE

class AttendanceWindow(QWidget):
    def __init__(self, post_db, mongo_db, parent=None):
        super().__init__(parent)
        self.post_db = post_db
        self.mongo_db = mongo_db
        self.face_recognizer = FaceRecongnizer()
        self.setWindowTitle("Mark Attendance")
        self.resize(400, 300)

        layout = QVBoxLayout()

        self.label = QLabel("Click the button below to mark your attendance.")
        self.btn_mark = QPushButton("Mark Attendance")

        layout.addWidget(self.label)
        layout.addWidget(self.btn_mark)
        self.setLayout(layout)

        self.btn_mark.clicked.connect(self.mark_attendance)

        # Track marked employees in this session to avoid duplicates
        self._marked_today = set()

        # Preload encodings once per session
        self.ids, self.encodings, self.meta = self._prepare_known_encodings()
        if len(self.ids) == 0:
            QMessageBox.warning(self, "No employees", "No employee encodings found. Register employees first.")
            return      

    def _prepare_known_encodings(self):
        """
        Load known encodings from Postgres into memory for fast comparison.
        Returns tuple (ids_list, encodings_array, meta_list)
        """
        rows = self.post_db.get_all_encodings()
        if not rows:
            return [], np.empty((0, 128)), []
        
        ids = []
        encodings_list = []
        meta = {}

        for r in rows:
            # Ensure each face_encoding is a numpy array of shape(128,)
            enc = np.array(r['face_encoding']).ravel()
            encodings_list.append(enc)
            ids.append(r['employee_id'])
            meta[r['employee_id']] = {
                'employee_id': r['employee_id'], 
                'name': r['name'], 
                'department': r['department']
                }
            
            encodings = np.stack(encodings_list)    # shape: (num_employees, 128)
        return ids, encodings, meta


    def _match_encodings(self, live_encoding, ids, encodings, tolerance=FACE_MATCH_TOLERANCE):
        """
        Vectorized match: compute Euclidean distances, find smallest.
        Returns (employee_id, distance) or (None, None)
        """
        if encodings.shape[0] == 0:
            return None, None
        
        # Ensure 1D
        live_encoding = np.ravel(live_encoding)
        if live_encoding.shape[0] != 128:
            print("Warning: live encoding has wrong shape", live_encoding.shape)
            return None, None
        
        # Compute Euclidean distances
        difference = encodings - live_encoding  # broadcasting
        distance = np.linalg.norm(difference, axis=1)
        idx = int(np.argmin(distance))

        # Safety check
        if idx >= len(ids):
            print(f"Safety: idx {idx} out of bounds for ids of length {len(ids)}")
            return None, None
        
        best_distance = float(distance[idx])
        if best_distance <= tolerance:
            return ids[idx], best_distance
        return None, None
    

    def mark_attendance(self) -> None:
        # step 1: Open the camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            QMessageBox.critical(self, "Error", "Could not access camera.")
            return
        
        QMessageBox.information(self, "Info", "Attendance session started. Press Esc to stop.")

        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                QMessageBox.critical(self, "Error", "Failed to capture image.")
                break
            
            frame_count += 1    # process every 3rd frame
            if (frame_count % 3) != 0:
                cv2.imshow("Mark Attendance - Esc to exit", frame)
                if cv2.waitKey(1) == 27:    # Esc key
                    break
                continue

            # Extract encodings from frame
            face_encodings = self.face_recognizer.extract_face_encoding(frame)
            if face_encodings is None or len(face_encodings) == 0:
                cv2.imshow("Mark Attendance - Esc to exit", frame)
                if cv2.waitKey(1) == 27:    # Esc key
                    break
                continue

            for enc in face_encodings:
                enc = np.ravel(enc)
                employee_id, distance = self._match_encodings(enc, self.ids, self.encodings)
                if employee_id is None:
                    print(f"Face detected but no match. Distance: {distance}, Tolerance: {FACE_MATCH_TOLERANCE}")
                    continue
                # remove after testing
                print(f"Employee_id found. Distance: {distance}")

                if employee_id in self._marked_today:
                    print(f"Attendance already marked for {employee_id}. Skipping.")
                    continue

                # Mark attendance    
                employee = self.meta.get(employee_id)
                record = {
                    "employee_id": employee_id,
                    "name": employee["name"],
                    "department": employee["department"],
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "status": "Present",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                try:
                    self.mongo_db.log_attendance(record)
                    self._marked_today.add(employee_id)
                    self.label.setText(f"Attendance marked for {employee['name']}")
                    break   # Stop after first valid match (avoid multi-person confusion)
                except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to log attendance: {e}")

            cv2.imshow("Mark Attendance - Esc to exit", frame)
            if cv2.waitKey(1) == 27:
                break

        cap.release()
        cv2.destroyAllWindows()
