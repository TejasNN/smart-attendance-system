# Face encoding extraction with validation.
import cv2
import face_recognition
import numpy as np
from typing import List, Tuple

class FaceRecongnizer:
    @staticmethod
    def extract_face_encoding(frame: np.ndarray) -> Tuple[List[np.ndarray], List[Tuple[int,int,int,int]]]:
        """
        Returns:
          - encodings: list of 1D numpy arrays (length 128)
          - locations: list of face_locations as (top, right, bottom, left) but in the small frame coords
        Note: frame is OpenCV BGR (original size). We downscale internally for speed.
        """
        if frame is None:
            return [], []
        
        # Downscale to 1/4 size for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25,fy=0.25)

        # Convert BGR (OpenCV) -> RGB (face_recognition)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Detect face locations
        face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")

        if not face_locations:
            return [], []

        # Generate the encodings
        face_encoding = face_recognition.face_encodings(rgb_small_frame, face_locations)

        # convert to 1D arrays
        encodings = [np.ravel(enc) for enc in face_encoding]
        return encodings, face_locations