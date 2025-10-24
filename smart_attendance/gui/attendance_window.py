import cv2
import time
import numpy as np
import threading
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, 
    QSizePolicy, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    QThreadPool, Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QAbstractAnimation
)
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor
 
from threads.camera_thread import CameraThread
from threads.recognition_worker import RecognitionWorker
from services.face_recognizer import FaceRecongnizer
from services.attendance_record import AttendanceRecord

from config import FACE_MATCH_TOLERANCE
from config import FACE_SKIP_INTERVAL

class AttendanceWindow(QWidget):
    FEEDBACK_DURATION_MS = 3000     # how long the feedback label stays visible
    FACE_PERSISTENCE_SECONDS = 2.0  # how long to keep a drawn rectangle if not updated

    def __init__(self, post_db, mongo_db, parent=None):
        super().__init__(parent)
        self.post_db = post_db
        self.mongo_db = mongo_db
        self.face_recognizer = FaceRecongnizer()

        self.setWindowTitle("Mark Attendance")
        self.resize(600, 400) 

        # layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        # Video preview label (will expand to fill available space)
        self.video_label = QLabel("Camera feed will appear here")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_label.setMinimumSize(320,200)    # reasonable minimum
        self.video_label.setScaledContents(False)   # prevent pixmap from changing label size
        layout.addWidget(self.video_label)

        # Floating start/Stop button overlaid on video_label
        self.btn_toggle = QPushButton("Start Attendance", self.video_label)
        self.btn_toggle.setFixedSize(160, 40)
        self.btn_toggle.setStyleSheet("background-color: green; color: white; font-weight: bold")
        self.btn_toggle.clicked.connect(self.toggle_session)
        self.btn_toggle.raise_()

        # Feedback label (overlay)
        self.feedback_label = QLabel("", self.video_label)
        self.feedback_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.feedback_label.setStyleSheet("""
            QLabel {
                background-color: rgba(46, 204, 113, 180);
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 8px 14px;
                border-radius: 10px;
            }
        """)
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback_label.hide()
        self.feedback_timer = QTimer()
        self.feedback_timer.setSingleShot(True)
        self.feedback_timer.timeout.connect(self.feedback_label.hide)

        self.setLayout(layout)

        # Camera thread will be created when starting session (so we can recreate it each time)
        self.camera_thread = None

        # Thread pool for recognition workers
        self.thread_pool = QThreadPool()

        # Track marked employees in this session to avoid duplicates
        self._marked_today = set()  
        
        # Track currently detected faces for persistent rectangle drawing
        # key: employee_id, value: (bbox, last_seen_timestamp)
        self.current_faces = {}

        # Initiate threading lock
        self._attendance_lock = threading.Lock()


        # Preload encodings once per session
        self.ids, self.encodings, self.meta = self._prepare_known_encodings()
        if len(self.ids) == 0:
            QMessageBox.warning(self, "No employees", "No employee encodings found. Register employees first.")
            self.show_feedback("No employee found - please register first", "error")
            return

        # State
        self._running = False
        self.frame_count = 0

        # Initialize green idle glow on start attendance button
        self.add_pulse_effect("#00cc66")


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
        
        encodings = np.stack(encodings_list) if encodings_list else np.empty((0, 128))   # shape: (num_employees, 128)
        return ids, encodings, meta
    

    def toggle_session(self):
        if not self._running:
            self.start_session()
        else:
            self.stop_session()


    def start_session(self):
        # create a fresh CameraThread each time we start
        if self.camera_thread is not None:
            # if an old thread reference exits, ensure it's stopped/cleaned
            try:
                self.camera_thread.stop()
            except Exception:
                pass
        
        self.camera_thread = CameraThread()
        # Connect signal (always connect the new thread's signal)
        self.camera_thread.frame_ready.connect(self.update_frame)

        # Start thread
        self.camera_thread.start()
        self._running = True
        self.btn_toggle.setText("Stop Attendance")
        self.btn_toggle.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        self.add_pulse_effect("#ff4d4d")    # soft red glow
        print("Attendance session started")
        self.show_feedback("Camera started", "info")


    def stop_session(self):
        # Flip running flag
        self._running = False

        # Disconnect frame handler (safe disconnect)
        if self.camera_thread is not None:
            try:
                self.camera_thread.frame_ready.disconnect(self.update_frame)
            except Exception:
                pass  # already disconnected

            # Stop the thread and wait for it to finish
            try:
                self.camera_thread.stop()
            except Exception as e:
                print("Error stopping camera thread: ", e)

            # Drop reference so a new one will be created next start
            self.camera_thread = None

        # Reset the UI
        self.video_label.clear()
        self.video_label.setStyleSheet("background-color: black; color: white;")
        self.video_label.setText("Camera Stopped")
        self.current_faces.clear()
        self._marked_today.clear()

        # toggle button back to 'start state (green)
        self.remove_pulse_effect()
        self.btn_toggle.setText("Start Attendance")
        self.add_pulse_effect("#00cc66")    # soft green glow for idle state
        self.btn_toggle.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        self.show_feedback("Camera Stopped", "info")

        # Ensure feedback timer is stopped and label hidden
        try:
            self.feedback_timer.stop()
            self.feedback_label.hide()
        except Exception:
            pass

        print("Attendance session ended")
    

    def on_worker_error(self, error_message):
        # Runs on main thread; log the error
        print("[RecognitionWorker ERROR]", error_message)


    def update_frame(self, frame: np.ndarray) -> None:
        # If session was stopped between frames, ignore
        if not self._running:
            return
        
        self.frame_count += 1

        current_time = time.time()

        # Remove faces that haven't been updated recently (e.g., 1 sec)
        self.current_faces = {emp: (b, t) for emp, (b, t) in self.current_faces.items()
                              if current_time - t < self.FACE_PERSISTENCE_SECONDS}
        
        # Draw rectangles for all currently detected faces
        for emp_id, (bbox, _) in self.current_faces.items():
            x, y, w, h = bbox
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            name = self.meta.get(emp_id, {}).get("name", "Unknown")
            cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)


        # Display frame in QLabel scaled to the video label size (maintain aspect ratio)
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pix = QPixmap.fromImage(qt_img)
            # Scale to video_label's current size 
            target_size = self.video_label.size()
            if target_size.width() > 0 and target_size.height() > 0:
                scaled = pix.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, 
                                    Qt.TransformationMode.SmoothTransformation)
            else:
                scaled = pix
            self.video_label.setPixmap(scaled)
        except Exception as e:
            print("Error rendering frame: ", e)

        # Send every nth frame to recognition worker
        if self.frame_count % FACE_SKIP_INTERVAL == 0:
            worker = RecognitionWorker(
                frame.copy(),
                self.ids,
                self.encodings,
                self.meta,
                FACE_MATCH_TOLERANCE,
                self.face_recognizer
            )
            # Connect worker signal to main-thread handlers
            worker.signals.result.connect(self.handle_recognition_result)
            worker.signals.error.connect(self.on_worker_error)
            self.thread_pool.start(worker)
        

    def handle_recognition_result(self, employee_id, bbox):
        # Update current_faces dict with new bbox and timestamp
        self.current_faces[employee_id] = (bbox, time.time())

        with self._attendance_lock:
            if self.mongo_db.check_valid_entry_for_date(employee_id):
                print(f"Attendance already marked for {employee_id} for today.")
                return

            if employee_id in self._marked_today:
                print(f"Attendance already marked for {employee_id}. Skipping.")
                return  # Already marked in this session
            
            employee = self.meta.get(employee_id)
            if not employee:
                print(f"Unknown employee id {employee_id}")

            record = AttendanceRecord(
                employee_id=employee_id,
                name=employee["name"],
                department=employee["department"],
                status="Present",
                marked_by="System"
            )
            try:
                success = self.mongo_db.log_attendance(record.to_dict())
                if success:
                    self._marked_today.add(employee_id)
                    self.show_feedback(f"Attendance marked for {employee['name']}", "success")
                    print(f"Attendance marked for {employee['name']}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error: Failed to log attendance: {e}")
                self.show_feedback("Error logging attendance", "error")

    
    # Feedback overlay helpers
    def show_feedback(self, message: str, message_type: str = "info") -> None:
        """Show adaptive feedback message (success, error, info) with fade-out animation."""
        # Define color themes
        colors = {
            "success": "rgba(46, 204, 113, 200)",   # Green
            "error": "rgba(231, 76, 60, 200)",      # red
            "info": "rgba(52, 152, 219, 200)"       # blue       
        }      
        color = colors.get(message_type, colors["info"])

        # Style label dynamically
        self.feedback_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 10px;
            }}
        """)

        # Initialize opacity effect if not done already
        if not hasattr(self, "feedback_opacity"):
            self.feedback_opacity = QGraphicsOpacityEffect()
            self.feedback_label.setGraphicsEffect(self.feedback_opacity)
            self.feedback_opacity.setOpacity(1.0)
        
        # Stop any running fade animation
        self.stop_running_animation()

        # Set feedback message
        self.feedback_label.setText(message)
        self.feedback_label.adjustSize()

        # Position message at the top-center of the video feed label
        w = self.video_label.width()
        mw = self.feedback_label.width()
        x = (w - mw) // 2
        y = 20 # top margin
        self.feedback_label.move(max(0, x), y)
        
        # Reset full opacity and show the label
        self.feedback_opacity.setOpacity(1.0)
        self.feedback_label.show()

        # Timer to delay fade start (so message stays for a few seconds)
        QTimer.singleShot(self.FEEDBACK_DURATION_MS, self.start_feedback_fade)

    
    def stop_running_animation(self):
        """Safely stop fade animation if it's running."""
        if hasattr(self, "fade_anim") and self.fade_anim.state() == QAbstractAnimation.State.Running:
            self.fade_anim.stop()


    def start_feedback_fade(self):
        """Starts the fade-out animation for feedback label."""
        if not hasattr(self, "feedback_opacity"):
            return
        
        self.fade_anim = QPropertyAnimation(self.feedback_opacity, b"opacity")
        self.fade_anim.setDuration(2000)    # 2 second fade
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_anim.finished.connect(self.feedback_label.hide)
        self.fade_anim.start()

    
    def add_pulse_effect(self, color: str) -> None:
        """Add a soft pulsing glow effect to the toggle button"""
        # Drop shadow for glow
        glow = QGraphicsDropShadowEffect(self.btn_toggle)
        glow.setColor(QColor(color))
        glow.setBlurRadius(30)
        glow.setOffset(0, 0)
        self.btn_toggle.setGraphicsEffect(glow)

        # Animation for pulsing
        self.glow_anim = QPropertyAnimation(glow, b"blurRadius")
        self.glow_anim.setDuration(1200)
        self.glow_anim.setStartValue(15)
        self.glow_anim.setEndValue(40)
        self.glow_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.glow_anim.setLoopCount(-1)
        self.glow_anim.start()

    
    def remove_pulse_effect(self):
        """Remove the pulsing glow effect from the toggle button."""
        if hasattr(self, "glow_anim"):
            self.glow_anim.stop()
            del self.glow_anim
        self.btn_toggle.setGraphicsEffect(None)

    # Keep the floating elements positioned correctly when window/responsive changes
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position toggle button at bottom-right inside video label
        try:
            vbw = self.video_label.width()
            vbh = self.video_label.height()
            btn_x = self.video_label.x() + vbw - self.btn_toggle.width() - 20
            btn_y = self.video_label.y() + vbh - self.btn_toggle.height() - 20
            # Map coordinates are already in widget-local since btn_toggle parent is video_label
            self.btn_toggle.move(btn_x - self.video_label.x(), btn_y - self.video_label.y())
            # Keep feedbback centered
            fx = (vbw - self.feedback_label.width()) // 2
            self.feedback_label.move(max(0, fx), 20)
        except Exception:
            pass