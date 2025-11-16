import cv2
import numpy as np
import traceback
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal

class WorkerSignals(QObject):
    # emits tuple (employee_id: str, bbox: tuple)
    result = pyqtSignal(object, object)
    error = pyqtSignal(str)

class RecognitionWorker(QRunnable):
    """
    Worker for heavy face recognition logic.
    Runs in QThreadpool.
    """

    def __init__(self, frame, ids, encodings, meta, tolerance, face_recognizer):
        super().__init__()
        self.frame = frame
        self.ids = ids
        self.encodings = encodings
        self.meta = meta
        self.tolerance = tolerance
        self.face_recognizer = face_recognizer
        self.signals = WorkerSignals()

    def run(self):
        try:
            face_encodings, face_locations = self.face_recognizer.extract_face_encoding(self.frame)
            if not face_encodings or not face_locations:
                return
            
            for encoding, location in zip(face_encodings, face_locations):
                enc = np.ravel(encoding)
                employee_id, distance = self._match_encodings(enc, self.ids, self.encodings, self.tolerance)
                # scale back loc (since face_recognition runs on 0.25 size frame)
                top, right, bottom, left = location
                scale = 4
                bbox = (left*scale, top*scale, (right-left)*scale, (bottom-top)*scale)
                if employee_id is None:
                    print("Face detected but no match.")
                    continue
                # Emit result (this will be delivered to GUI/main thread)
                self.signals.result.emit(employee_id, bbox)
        except Exception as e:
            tb = traceback.format_exc()
            self.signals.error.emit(f"{e}\n{tb}")

    def _match_encodings(self, live_encoding, ids, encodings, tolerance):
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