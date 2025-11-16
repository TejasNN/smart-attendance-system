import cv2
import time
from PyQt6.QtCore import QThread, pyqtSignal

class CameraThread(QThread):
    frame_ready = pyqtSignal(object)    # emits raw OpenCV frame

    def __init__(self, parent = None):
        super().__init__(parent)
        self._running = False
        self._cap = None

    def run(self):
        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            print("Error: Could not access camera.")
            return
        self._running = True

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                break
            self.frame_ready.emit(frame)
            time.sleep(0.03)    # ~30 FPS

        self._cap.release()

    def stop(self):
        self._running = False
        self.wait()

