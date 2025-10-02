import cv2
import time
import numpy as np
from datetime import datetime

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt6.QtCore import QThreadPool, Qt
from PyQt6.QtGui import QImage, QPixmap
 
from threads.camera_thread import CameraThread
from threads.recognition_worker import RecognitionWorker
from services.face_recognizer import FaceRecongnizer
from config import FACE_MATCH_TOLERANCE
from config import FACE_SKIP_INTERVAL

class AttendanceWindow(QWidget):
    def __init__(self, post_db, mongo_db, parent=None):
        super().__init__(parent)
        self.post_db = post_db
        self.mongo_db = mongo_db
        self.face_recognizer = FaceRecongnizer()

        self.setWindowTitle("Mark Attendance")
        self.resize(600, 400) 

        # layout
        layout = QVBoxLayout()

        # Video preview label
        self.video_label = QLabel("Camera feed will appear here")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        layout.addWidget(self.video_label)

        # Controls
        self.btn_toggle = QPushButton("Start Attendance")
        layout.addWidget(self.btn_toggle)
        self.setLayout(layout)

        # Camera + Threadpool
        self.camera_thread = CameraThread()
        self.camera_thread.frame_ready.connect(self.update_frame)
        self.thread_pool = QThreadPool()

        # Button click
        self.btn_toggle.clicked.connect(self.toggle_session)

        # Track marked employees in this session to avoid duplicates
        self._marked_today = set()  
        
        # Track currently detected faces for persistent rectangle drawing
        # key: employee_id, value: (bbox, last_seen_timestamp)
        self.current_faces = {}

        # Preload encodings once per session
        self.ids, self.encodings, self.meta = self._prepare_known_encodings()
        if len(self.ids) == 0:
            QMessageBox.warning(self, "No employees", "No employee encodings found. Register employees first.")
            return

        # State
        self._running = False
        self.frame_count = 0


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
    

    def toggle_session(self):
        if not self._running:
            self.start_session()
        else:
            self.stop_session()

    def start_session(self):
        self._running = True
        self.btn_toggle.setText("Stop Attendance")
        self.camera_thread.start()
        print("Attendance session started")

    def stop_session(self):
        self._running = False

        # Block any further frames
        try:
            self.camera_thread.frame_ready.disconnect(self.update_frame)
        except TypeError:
            pass  # already disconnected

        # Reset the UI
        self.video_label.clear()
        self.video_label.setStyleSheet("background-color: black; color: white;")
        self.video_label.setText("Camera Stopped")
        print("Attendance session ended")

        self.btn_toggle.setText("Start Attendance")

        self.camera_thread.stop()

    def update_frame(self, frame: np.ndarray) -> None:
        self.frame_count += 1

        current_time = time.time()

        # Remove faces that haven't been updated recently (e.g., 1 sec)
        self.current_faces = {emp: (b, t) for emp, (b, t) in self.current_faces.items()
                              if current_time - t < 1.0}
        
        # Draw rectangles for all currently detected faces
        for emp_id, (bbox, _) in self.current_faces.items():
            x, y, w, h = bbox
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            name = self.meta.get(emp_id, {}).get("name", "Unknown")
            cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)


        # Display frame in QLabel
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

        # Send every nth frame to recognition worker
        if self.frame_count % FACE_SKIP_INTERVAL == 0:
            worker = RecognitionWorker(
                frame.copy(),
                self.ids,
                self.encodings,
                self.meta,
                FACE_MATCH_TOLERANCE,
                self.handle_recognition_result,
                self.face_recognizer
            )
            self.thread_pool.start(worker)
        

    def handle_recognition_result(self, employee_id, bbox, frame):
        # Update current_faces dict with new bbox and timestamp
        self.current_faces[employee_id] = (bbox, time.time())

        x, y, w, h = bbox

        if frame is None:
            return
        
        # Draw rectangle
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Put name
        name = "Unknown"
        if employee_id:
            employee = self.meta.get(employee_id)

            if employee:
                name = employee.get("name")
                print(f"Employee {name} found!")
        else:
            print("Employee {name}.")

        cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Now convert and update video_label
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

        if self.mongo_db.check_valid_entry_for_date(employee_id):
            print(f"Attendance already marked for {employee_id} for today.")
            return

        if employee_id in self._marked_today:
            print(f"Attendance already marked for {employee_id}. Skipping.")
            return  # Already marked in this session

        record = {
            "employee_id": employee_id,
            "name": employee["name"],
            "department": employee["department"],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "Present",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        try:
            success = self.mongo_db.log_attendance(record)
            if success:
                self._marked_today.add(employee_id)
                self.video_label.setText(f"Attendance marked for {employee['name']}")
                print(f"Attendance marked for {employee['name']}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: Failed to log attendance: {e}")