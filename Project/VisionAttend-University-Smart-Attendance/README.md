# VisionAttend – University Smart Attendance System

VisionAttend is a face-verification-based attendance management system developed for universities. It automatically verifies students, records attendance, and calculates subject-wise attendance percentages.

## Project Details

- **Student Name:** V Sreekanth
- **Register Number:** 192372037
- **Department:** Computer Science and Engineering
- **Project Type:** Computer Vision Project

## Objective

To develop a secure university attendance system that verifies student faces and records attendance automatically.

## Main Module

Face Verification and Attendance Management

## Features

- Student face registration
- LBPH face-model training
- Real-time face verification
- Automatic attendance marking
- Teacher permission attendance
- Draft and submitted attendance sessions
- Slot-based master timetable
- Subject and class management
- Student course enrolment
- Subject-wise attendance percentage
- Detailed attendance reports
- Admin, Teacher, and Student dashboards
- Secure Change Password option for all users

## User Roles

### Admin

- Manage departments
- Manage classes and subjects
- Create teacher and student accounts
- Register student faces
- Train the face-recognition model
- Assign courses and slots
- Manage the timetable
- View attendance reports
- Change own password

### Teacher

- View assigned courses
- Start attendance sessions
- Verify students using the camera
- Give permission attendance with a reason
- Submit or cancel attendance
- View reports
- Change own password

### Student

- View enrolled subjects
- Check conducted and attended classes
- View attendance percentage
- Change own password

## Tools and Technologies

- Python
- Flask
- OpenCV
- LBPH Face Recognizer
- MySQL
- PyMySQL
- HTML
- CSS
- Jinja2
- Werkzeug Security
- Visual Studio Code
- XAMPP

## Installation

### 1. Install the required packages

```bash
python -m pip install -r requirements.txt
```

### 2. Start MySQL

Open XAMPP Control Panel and start MySQL.

### 3. Configure the database

Check the MySQL settings inside `config.py`.

### 4. Initialize the database

```bash
python init_db.py
```

### 5. Run the application

```bash
python app.py
```

### 6. Open the website

Open `http://127.0.0.1:5000` in a web browser.

## Face Registration Process

1. Admin creates the student account.
2. Admin clicks **Register Face**.
3. The system captures approximately 30 face images.
4. Admin clicks **Train Face Model**.
5. The trained model verifies enrolled students during attendance.

## Attendance Workflow

1. Teacher opens the scheduled subject.
2. Attendance is created in Draft status.
3. The camera verifies enrolled students.
4. Recognized students are marked Present.
5. Teacher may provide permission attendance with a reason.
6. Teacher submits attendance.
7. Remaining pending students are marked Absent.
8. Submitted attendance is included in percentage calculations.

## Folder Structure

```text
VisionAttend-University-Smart-Attendance
│
├── app.py
├── config.py
├── database.sql
├── face_service.py
├── init_db.py
├── requirements.txt
├── dataset
│   └── .gitkeep
├── trainer
│   └── .gitkeep
├── static
│   └── css
│       └── style.css
└── templates
    ├── login.html
    ├── base.html
    ├── admin_dashboard.html
    ├── teacher_dashboard.html
    ├── student_dashboard.html
    ├── attendance_session.html
    ├── attendance_reports.html
    └── change_password.html
```

## Privacy and Security

Student face photographs and the trained face model are not uploaded to GitHub. Passwords are securely stored using password hashing.

## Outcome

Student faces are verified and attendance is recorded automatically and securely.
