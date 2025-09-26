# Smart Attendance System (Face Recognition + PyQt6)

## 📌 Overview
A desktop-based **Smart Attendance System** that automates employee attendance using **face recognition**.  
Built with **Python, PyQt6, OpenCV, dlib/face_recognition, PostgreSQL, and MongoDB**.  

This project demonstrates skills in **GUI development, computer vision, databases, and threading**.  

---

## 🚀 Features
- Employee **registration with photo & face encoding** (stored in PostgreSQL).  
- **Real-time attendance marking** using webcam + face recognition.  
- Dual-database approach:  
  - PostgreSQL → structured employee metadata & encodings.  
  - MongoDB → attendance logs with timestamps.  
- **Duplicate prevention** → ensures one log per employee per day.  
- **Green bounding box** around detected faces for visual feedback.  
- **Non-blocking camera** using PyQt QThread worker (avoids GUI freeze).  

---

## 🛠️ Tech Stack
- **Python 3.10+**
- **PyQt6** (GUI)
- **OpenCV** (camera handling)
- **face_recognition/dlib** (face encodings & matching)
- **PostgreSQL** (employee data)
- **MongoDB** (attendance logs)

---

## 📂 Project Structure

```bash
smart_attendance/
│   config.example.py
│   main.py
│
├───database
│       mongo_db.py
│       postgres_db.py
│
├───gui
│       attendance_window.py
│       logs_window.py
│       main_window.py
│       register_window.py
│
├───services
│       attendance_worker.py
│       face_recognizer.py
│       photo_storage.py
│
└───utils
        utils.py
```

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/<your-username>/smart-attendance-system.git
cd smart-attendance-system
```

### 2️⃣ Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
venv\Scripts\activate     # On Windows
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Setup Databases

PostgreSQL: Create DB & run create_tables() in postgres_db.py.

MongoDB: Ensure service is running (mongod).


### 5️⃣ Run the app

python main.py

---

## 🌟 Future Enhancements

- 📊 Export logs as Excel/PDF reports
- 🔑 Add login roles (Admin/User)
- 🛡️ Strengthen validation & security
- 📈 Build interactive dashboards for admins

---

## 🙌 Challenges & Learnings

- Learned PyQt threading to prevent GUI freezing.

- Designed a dual-database architecture.

- Improved face recognition accuracy with encoding optimizations.

- Implemented validation checks to avoid duplicate logs.

---

## 📸 Demo



---

#### 👤 Author

Developed by @TejasNN (Tejas Nagvekar)
🚀 Passionate about building scalable desktop and web applications with Python.

