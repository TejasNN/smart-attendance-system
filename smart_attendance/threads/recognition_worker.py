import cv2
import numpy as np
from PyQt6.QtCore import QRunnable

class RecognitionWorker(QRunnable):
    """
    Worker for heavy face recognition logic.
    Runs in QThreadpool.
    """

    def __init__(self, frame, ids, encodings, meta, tolerance, callback, face_recognizer):
        super().__init__()
        self.frame = frame
        self.ids = ids
        self.encodings = encodings
        self.meta = meta
        self.tolerance = tolerance
        self.callback = callback
        self.face_recognizer = face_recognizer

    def run(self):
        face_encodings = self.face_recognizer.extract_face_encoding(self.frame)
        if face_encodings is None or len(face_encodings) == 0:
            return
        
        for enc in face_encodings:
            enc = np.ravel(enc)
            employee_id, distance = self._match_encodings(enc, self.ids, self.encodings, self.tolerance)
            if employee_id is None:
                print("Face detected but no match.")
                continue
            self.callback(employee_id)

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