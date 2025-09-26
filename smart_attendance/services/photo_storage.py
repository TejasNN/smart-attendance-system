# Add methods for saving temp photos, moving to permanent, and cleanup.

import os
import shutil
import cv2

class PhotoStorage:
    TEMP_DIR = "temp_photos"
    PERM_DIR = "photos"

    @staticmethod
    def save_temp_photo(frame) -> str:
        os.makedirs(PhotoStorage.TEMP_DIR, exist_ok=True)
        temp_path = os.path.join(PhotoStorage.TEMP_DIR, "temp_photo.jpg")
        cv2.imwrite(temp_path, frame)
        return temp_path
    
    @staticmethod
    def move_to_employee_folder(emp_id: int, temp_path: str) -> str:
        emp_dir = os.path.join(PhotoStorage.PERM_DIR, str(emp_id))
        os.makedirs(emp_dir, exist_ok=True)
        final_photo_path = os.path.join(emp_dir, "photo.jpg")
        shutil.move(temp_path, final_photo_path)
        return final_photo_path
