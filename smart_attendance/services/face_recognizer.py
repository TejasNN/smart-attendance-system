# Face encoding extraction with validation.
import cv2
import face_recognition
import numpy as np
from typing import List

class FaceRecongnizer:
    @staticmethod
    def extract_face_encoding(frame: np.ndarray):
        """
        Extracts face encodings from a given frame (OpenCV BGR numpy array).
        Downscales frame for performance, converts to RGB, detects faces, 
        and returns list of encodings (may be empty).
        """
        # Downscale to 1/4 size for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25,fy=0.25)

        # Convert BGR (OpenCV) -> RGB (face_recognition)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Detect face locations
        face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")

        if not face_locations:
            return None

        # Draw rectangles around the detected faces
        for (top, right, bottom, left) in face_locations:
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.imshow("Attendance", frame)

        # Generate the encodings
        face_encoding = face_recognition.face_encodings(rgb_small_frame, face_locations)

        return [np.ravel(enc) for enc in face_encoding]
    
    @staticmethod   
    def distance(self, enc1: np.ndarray, enc2: np.ndarray) -> float:
        """Euclidean distance between encodings."""
        return float(np.linalg.norm(enc1 - enc2))