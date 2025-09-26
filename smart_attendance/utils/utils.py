import os
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QWidget

def reset_fields(self) -> None:
    # Remove temp photo if exists
    if self.photo_path and os.path.exists(self.photo_path):
        try:
            os.remove(self.photo_path)
        except Exception as e:
            print(f"Could not remove temp file {self.photo_path}: {e}")

    self.name_input.clear()
    self.dept_input.setCurrentIndex(0)
    self.photo_path = None

def center_window(window: QWidget) -> None:
    screen = QGuiApplication.primaryScreen().availableGeometry()
    frame = window.frameGeometry()
    frame.moveCenter(screen.center())
    window.move(frame.topLeft())
