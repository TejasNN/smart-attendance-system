# import cv2
# import numpy as np
# from PyQt6.QtCore import QThread, pyqtSignal
# from datetime import datetime
# from config import FACE_MATCH_TOLERANCE

# class AttendanceWorker(QThread):
#     attendance_marked = pyqtSignal(str)     # emits employee name when marked
#     error_occured = pyqtSignal(str)
#     finished = pyqtSignal(str)

#     def __init__(self, face_recognizer, mongo_db, ids, encodings, meta, parent = None):
#         super().__init__(parent)
#         self.face_recognizer = face_recognizer
#         self.mongo_db = mongo_db
#         self.ids = ids
#         self.encodings = encodings
#         self.meta = meta
#         self._marked_today = set()
#         self._running = True

#     def run(self):
#         # step 1: Open the camera
#         cap = cv2.VideoCapture(0)
#         if not cap.isOpened():
#             self.error_occured.emit("Error: Could not access camera.")
#             self.finished.emit()
#             return
        
#         self.status_update.emit("Attendance session started. Press Esc to stop.")
        
#         frame_count = 0
#         while self._running:
#             ret, frame = cap.read()
#             if not ret:
#                 self.error_occured.emit("Error: Failed to capture image.")
#                 break
#             frame_count += 1
#             if frame_count % 3 != 0:    # process every 3rd frame
#                 cv2.imshow("Mark Attendance - Esc to exit", frame)
#                 if cv2.waitKey(1) == 27:    # Esc key
#                     break
#                 continue

#             # Extract encodings from frame
#             face_encodings = self.face_recognizer.extract_face_encoding(frame)
#             if face_encodings is None or len(face_encodings) == 0:
#                 cv2.imshow("Mark Attendance - Esc to exit", frame)
#                 if cv2.waitKey(1) == 27:    # Esc key
#                     break
#                 continue

#             for enc in face_encodings:
#                 enc = np.ravel(enc)
#                 employee_id, distance = self._match_encodings(enc, self.ids, self.encodings)

#                 if employee_id is None and self._marked_today:
#                     continue

#                 employee = self.meta.get(employee_id)
#                 if not employee:
#                     continue

#                 record = {
#                     "employee_id": employee_id,
#                     "name": employee["name"],
#                     "department": employee["department"],
#                     "date": datetime.now().strftime("%Y-%m-%d"),
#                     "status": "Present",
#                     "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#                 }
#                 try:
#                     success = self.mongo_db.log_Attendance(record)
#                     if success:
#                         self._marked_today.add(employee_id)
#                         self.attendance_marked.emit(employee["name"])
#                         print(f"Attendance marked for {employee['name']}")
#                     else:
#                         print(f"Attendance already exists for {employee['name']} on {record['date']}")
#                         break
#                 except Exception as e:
#                     self.error_occurred.emit(f"Error: Failed to log attendance: {e}")
            
#             # Emit frame for UI preview
#             self.frame_captured.emit(frame)

#             if cv2.waitKey(1) == 27:
#                 break

#         cap.release()
#         cv2.destroyAllWindows()
#         self.finished.emit()

#     def stop(self):
#         self._running = False

#     def _match_encodings(self, live_encoding, ids, encodings, tolerance=FACE_MATCH_TOLERANCE):
#         """
#         Vectorized match: compute Euclidean distances, find smallest.
#         Returns (employee_id, distance) or (None, None)
#         """
#         import face_recognition
#         distances = face_recognition.face_distance(encodings, live_encoding)
#         min_distance = np.min(distances)
#         if min_distance > tolerance:
#             return None, min_distance
#         idx = np.argmin(distances)
#         return ids[idx], min_distance
#         # if encodings.shape[0] == 0:
#         #     return None, None
        
#         # # Ensure 1D
#         # live_encoding = np.ravel(live_encoding)
#         # if live_encoding.shape[0] != 128:
#         #     print("Warning: live encoding has wrong shape", live_encoding.shape)
#         #     return None, None
        
#         # # Compute Euclidean distances
#         # difference = encodings - live_encoding  # broadcasting
#         # distance = np.linalg.norm(difference, axis=1)
#         # idx = int(np.argmin(distance))

#         # # Safety check
#         # if idx >= len(ids):
#         #     print(f"Safety: idx {idx} out of bounds for ids of length {len(ids)}")
#         #     return None, None
        
#         # best_distance = float(distance[idx])
#         # if best_distance <= tolerance:
#         #     return ids[idx], best_distance
#         # return None, None
