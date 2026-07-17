CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'teacher', 'student') NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    department_code VARCHAR(20) NOT NULL UNIQUE,
    department_name VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS classes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    department_id INT NOT NULL,
    class_name VARCHAR(100) NOT NULL,
    year_label VARCHAR(30) NOT NULL,
    section VARCHAR(20) NOT NULL,
    UNIQUE KEY uq_class (department_id, class_name, year_label, section),
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE TABLE IF NOT EXISTS slots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slot_code VARCHAR(10) NOT NULL UNIQUE,
    slot_name VARCHAR(40) NOT NULL
);

CREATE TABLE IF NOT EXISTS teachers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    employee_no VARCHAR(40) NOT NULL UNIQUE,
    full_name VARCHAR(120) NOT NULL,
    department_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL UNIQUE,
    register_no VARCHAR(40) NOT NULL UNIQUE,
    full_name VARCHAR(120) NOT NULL,
    class_id INT NOT NULL,
    face_registered BOOLEAN NOT NULL DEFAULT FALSE,
    face_folder VARCHAR(255) NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (class_id) REFERENCES classes(id)
);

CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(30) NOT NULL UNIQUE,
    subject_name VARCHAR(160) NOT NULL,
    department_id INT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE TABLE IF NOT EXISTS course_offerings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject_id INT NOT NULL,
    class_id INT NOT NULL,
    slot_id INT NOT NULL,
    teacher_id INT NOT NULL,
    academic_year VARCHAR(20) NOT NULL,
    semester VARCHAR(20) NOT NULL,
    room_name VARCHAR(80) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE KEY uq_offering (subject_id, class_id, slot_id, teacher_id, academic_year, semester),
    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (slot_id) REFERENCES slots(id),
    FOREIGN KEY (teacher_id) REFERENCES teachers(id)
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    offering_id INT NOT NULL,
    student_id INT NOT NULL,
    UNIQUE KEY uq_enrollment (offering_id, student_id),
    FOREIGN KEY (offering_id) REFERENCES course_offerings(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS slot_schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slot_id INT NOT NULL,
    day_of_week TINYINT NOT NULL COMMENT '0=Monday, 6=Sunday',
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_slot_schedule (
        slot_id, day_of_week, start_time, end_time
    ),
    FOREIGN KEY (slot_id) REFERENCES slots(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS timetable_entries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    offering_id INT NOT NULL,
    slot_schedule_id INT NULL,
    day_of_week TINYINT NOT NULL COMMENT '0=Monday, 6=Sunday',
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    room_name VARCHAR(80) NULL,
    FOREIGN KEY (offering_id) REFERENCES course_offerings(id) ON DELETE CASCADE,
    FOREIGN KEY (slot_schedule_id) REFERENCES slot_schedules(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS attendance_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    offering_id INT NOT NULL,
    timetable_entry_id INT NULL,
    session_date DATE NOT NULL,
    attendance_opened_at DATETIME NOT NULL,
    attendance_closes_at DATETIME NOT NULL,
    status ENUM('draft', 'submitted', 'cancelled') NOT NULL DEFAULT 'draft',
    created_by INT NOT NULL,
    submitted_at DATETIME NULL,
    cancel_reason VARCHAR(255) NULL,
    UNIQUE KEY uq_session (offering_id, session_date, timetable_entry_id),
    FOREIGN KEY (offering_id) REFERENCES course_offerings(id),
    FOREIGN KEY (timetable_entry_id) REFERENCES timetable_entries(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS attendance_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    student_id INT NOT NULL,
    status ENUM('present', 'present_permission', 'absent', 'pending') NOT NULL DEFAULT 'pending',
    method ENUM('face_recognition', 'teacher_permission', 'automatic') NOT NULL DEFAULT 'automatic',
    reason VARCHAR(255) NULL,
    marked_by INT NULL,
    marked_at DATETIME NULL,
    UNIQUE KEY uq_attendance_record (session_id, student_id),
    FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (marked_by) REFERENCES users(id) ON DELETE SET NULL
);
