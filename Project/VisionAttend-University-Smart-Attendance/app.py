from datetime import date, datetime, timedelta
from functools import wraps

import pymysql
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from pymysql.cursors import DictCursor
from werkzeug.security import check_password_hash, generate_password_hash

import config
from face_service import (
    MODEL_FILE,
    capture_student_faces,
    count_student_images,
    model_exists,
    recognize_enrolled_students,
    train_face_model,
)


app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY

DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def get_db():
    return pymysql.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


def query_all(sql, args=()):
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, args)
            return cursor.fetchall()
    finally:
        connection.close()


def query_one(sql, args=()):
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, args)
            return cursor.fetchone()
    finally:
        connection.close()


def execute(sql, args=()):
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, args)
            last_id = cursor.lastrowid
        connection.commit()
        return last_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()



def sync_slot_schedule(schedule_id):
    """
    Apply one master slot rule to all active course assignments
    that use the same slot.
    """

    connection = get_db()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    slot_id,
                    day_of_week,
                    start_time,
                    end_time
                FROM slot_schedules
                WHERE id=%s
                """,
                (schedule_id,),
            )
            schedule = cursor.fetchone()

            if not schedule:
                return 0

            cursor.execute(
                """
                SELECT id, room_name
                FROM course_offerings
                WHERE slot_id=%s AND is_active=1
                """,
                (schedule["slot_id"],),
            )
            offerings = cursor.fetchall()

            created = 0

            for offering in offerings:
                cursor.execute(
                    """
                    SELECT id
                    FROM timetable_entries
                    WHERE offering_id=%s
                      AND day_of_week=%s
                      AND start_time=%s
                      AND end_time=%s
                    LIMIT 1
                    """,
                    (
                        offering["id"],
                        schedule["day_of_week"],
                        schedule["start_time"],
                        schedule["end_time"],
                    ),
                )
                existing = cursor.fetchone()

                if existing:
                    cursor.execute(
                        """
                        UPDATE timetable_entries
                        SET slot_schedule_id=%s,
                            room_name=COALESCE(%s, room_name)
                        WHERE id=%s
                        """,
                        (
                            schedule_id,
                            offering["room_name"],
                            existing["id"],
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO timetable_entries
                        (
                            offering_id,
                            slot_schedule_id,
                            day_of_week,
                            start_time,
                            end_time,
                            room_name
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            offering["id"],
                            schedule_id,
                            schedule["day_of_week"],
                            schedule["start_time"],
                            schedule["end_time"],
                            offering["room_name"],
                        ),
                    )
                    created += 1

        connection.commit()
        return created

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def sync_offering_slot_schedules(offering_id):
    """
    When a new subject is assigned to Slot A/B/C/D, automatically
    create its weekly timetable from the master slot rules.
    """

    connection = get_db()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, slot_id, room_name
                FROM course_offerings
                WHERE id=%s
                """,
                (offering_id,),
            )
            offering = cursor.fetchone()

            if not offering:
                return 0

            cursor.execute(
                """
                SELECT id, day_of_week, start_time, end_time
                FROM slot_schedules
                WHERE slot_id=%s
                ORDER BY day_of_week, start_time
                """,
                (offering["slot_id"],),
            )
            schedules = cursor.fetchall()

            created = 0

            for schedule in schedules:
                cursor.execute(
                    """
                    SELECT id
                    FROM timetable_entries
                    WHERE offering_id=%s
                      AND day_of_week=%s
                      AND start_time=%s
                      AND end_time=%s
                    LIMIT 1
                    """,
                    (
                        offering_id,
                        schedule["day_of_week"],
                        schedule["start_time"],
                        schedule["end_time"],
                    ),
                )
                existing = cursor.fetchone()

                if existing:
                    cursor.execute(
                        """
                        UPDATE timetable_entries
                        SET slot_schedule_id=%s,
                            room_name=COALESCE(%s, room_name)
                        WHERE id=%s
                        """,
                        (
                            schedule["id"],
                            offering["room_name"],
                            existing["id"],
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO timetable_entries
                        (
                            offering_id,
                            slot_schedule_id,
                            day_of_week,
                            start_time,
                            end_time,
                            room_name
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            offering_id,
                            schedule["id"],
                            schedule["day_of_week"],
                            schedule["start_time"],
                            schedule["end_time"],
                            offering["room_name"],
                        ),
                    )
                    created += 1

        connection.commit()
        return created

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def sync_all_slot_schedules():
    schedules = query_all(
        "SELECT id FROM slot_schedules ORDER BY id"
    )

    created = 0

    for item in schedules:
        created += sync_slot_schedule(item["id"])

    return created


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))

            if role and session.get("role") != role:
                flash("You do not have permission to open that page.", "error")
                return redirect(url_for("dashboard"))

            return view(*args, **kwargs)

        return wrapped

    return decorator


def required_fields(form, names):
    missing = [name for name in names if not form.get(name, "").strip()]
    return missing


@app.context_processor
def inject_helpers():
    return {"DAY_NAMES": DAY_NAMES}


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = query_one(
            """
            SELECT id, username, password_hash, role, is_active
            FROM users
            WHERE username=%s
            """,
            (username,),
        )

        if (
            not user
            or not user["is_active"]
            or not check_password_hash(user["password_hash"], password)
        ):
            flash("Incorrect username or password.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.route("/change-password", methods=["GET", "POST"])
@login_required()
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not current_password or not new_password or not confirm_password:
            flash("Complete all password fields.", "error")
            return render_template("change_password.html")

        if len(new_password) < 8:
            flash("New password must contain at least 8 characters.", "error")
            return render_template("change_password.html")

        if new_password != confirm_password:
            flash("New password and confirmation do not match.", "error")
            return render_template("change_password.html")

        if current_password == new_password:
            flash("New password must be different from the current password.", "error")
            return render_template("change_password.html")

        user = query_one(
            """
            SELECT id, password_hash
            FROM users
            WHERE id=%s AND is_active=1
            """,
            (session["user_id"],),
        )

        if not user or not check_password_hash(
            user["password_hash"],
            current_password,
        ):
            flash("Current password is incorrect.", "error")
            return render_template("change_password.html")

        execute(
            """
            UPDATE users
            SET password_hash=%s
            WHERE id=%s
            """,
            (
                generate_password_hash(new_password),
                session["user_id"],
            ),
        )

        username = session.get("username", "User")
        session.clear()
        flash(
            f"Password changed successfully for {username}. "
            "Please login using the new password.",
            "success",
        )
        return redirect(url_for("login"))

    return render_template("change_password.html")


@app.route("/dashboard")
@login_required()
def dashboard():
    role = session["role"]

    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    if role == "teacher":
        return redirect(url_for("teacher_dashboard"))
    return redirect(url_for("student_dashboard"))


# -------------------------------------------------------------------
# ADMIN DASHBOARD AND MANAGEMENT
# -------------------------------------------------------------------

@app.route("/admin")
@login_required("admin")
def admin_dashboard():
    counts = {
        "departments": query_one("SELECT COUNT(*) count FROM departments")["count"],
        "classes": query_one("SELECT COUNT(*) count FROM classes")["count"],
        "subjects": query_one("SELECT COUNT(*) count FROM subjects")["count"],
        "teachers": query_one("SELECT COUNT(*) count FROM teachers")["count"],
        "students": query_one("SELECT COUNT(*) count FROM students")["count"],
        "offerings": query_one(
            "SELECT COUNT(*) count FROM course_offerings WHERE is_active=1"
        )["count"],
        "timetable": query_one(
            "SELECT COUNT(*) count FROM timetable_entries"
        )["count"],
    }

    slots = query_all(
        "SELECT slot_code, slot_name FROM slots ORDER BY slot_code"
    )

    return render_template(
        "admin_dashboard.html",
        counts=counts,
        slots=slots,
    )


@app.route("/admin/departments", methods=["GET", "POST"])
@login_required("admin")
def manage_departments():
    if request.method == "POST":
        code = request.form.get("department_code", "").strip().upper()
        name = request.form.get("department_name", "").strip()

        if not code or not name:
            flash("Department code and name are required.", "error")
        else:
            try:
                execute(
                    """
                    INSERT INTO departments (department_code, department_name)
                    VALUES (%s, %s)
                    """,
                    (code, name),
                )
                flash("Department added successfully.", "success")
                return redirect(url_for("manage_departments"))
            except pymysql.err.IntegrityError:
                flash("That department code already exists.", "error")

    departments = query_all(
        """
        SELECT
            d.id,
            d.department_code,
            d.department_name,
            COUNT(DISTINCT c.id) AS class_count,
            COUNT(DISTINCT s.id) AS subject_count,
            COUNT(DISTINCT t.id) AS teacher_count
        FROM departments d
        LEFT JOIN classes c ON c.department_id=d.id
        LEFT JOIN subjects s ON s.department_id=d.id
        LEFT JOIN teachers t ON t.department_id=d.id
        GROUP BY d.id, d.department_code, d.department_name
        ORDER BY d.department_code
        """
    )

    return render_template(
        "manage_departments.html",
        departments=departments,
    )


@app.route("/admin/classes", methods=["GET", "POST"])
@login_required("admin")
def manage_classes():
    if request.method == "POST":
        missing = required_fields(
            request.form,
            ["department_id", "class_name", "year_label", "section"],
        )

        if missing:
            flash("Complete every class field.", "error")
        else:
            try:
                execute(
                    """
                    INSERT INTO classes
                    (department_id, class_name, year_label, section)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        request.form["department_id"],
                        request.form["class_name"].strip(),
                        request.form["year_label"].strip(),
                        request.form["section"].strip().upper(),
                    ),
                )
                flash("Class and section added successfully.", "success")
                return redirect(url_for("manage_classes"))
            except pymysql.err.IntegrityError:
                flash("That class and section already exist.", "error")

    departments = query_all(
        """
        SELECT id, department_code, department_name
        FROM departments
        ORDER BY department_code
        """
    )

    classes = query_all(
        """
        SELECT
            c.id,
            c.class_name,
            c.year_label,
            c.section,
            d.department_code,
            COUNT(st.id) AS student_count
        FROM classes c
        JOIN departments d ON d.id=c.department_id
        LEFT JOIN students st ON st.class_id=c.id
        GROUP BY
            c.id, c.class_name, c.year_label, c.section,
            d.department_code
        ORDER BY d.department_code, c.year_label, c.section
        """
    )

    return render_template(
        "manage_classes.html",
        departments=departments,
        classes=classes,
    )


@app.route("/admin/subjects", methods=["GET", "POST"])
@login_required("admin")
def manage_subjects():
    if request.method == "POST":
        missing = required_fields(
            request.form,
            ["department_id", "subject_code", "subject_name"],
        )

        if missing:
            flash("Complete every subject field.", "error")
        else:
            try:
                execute(
                    """
                    INSERT INTO subjects
                    (subject_code, subject_name, department_id)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        request.form["subject_code"].strip().upper(),
                        request.form["subject_name"].strip(),
                        request.form["department_id"],
                    ),
                )
                flash("Subject added successfully.", "success")
                return redirect(url_for("manage_subjects"))
            except pymysql.err.IntegrityError:
                flash("That subject code already exists.", "error")

    departments = query_all(
        """
        SELECT id, department_code, department_name
        FROM departments
        ORDER BY department_code
        """
    )

    subjects = query_all(
        """
        SELECT
            s.id,
            s.subject_code,
            s.subject_name,
            d.department_code,
            COUNT(co.id) AS offering_count
        FROM subjects s
        JOIN departments d ON d.id=s.department_id
        LEFT JOIN course_offerings co ON co.subject_id=s.id
        GROUP BY
            s.id, s.subject_code, s.subject_name, d.department_code
        ORDER BY s.subject_code
        """
    )

    return render_template(
        "manage_subjects.html",
        departments=departments,
        subjects=subjects,
    )


@app.route("/admin/teachers", methods=["GET", "POST"])
@login_required("admin")
def manage_teachers():
    if request.method == "POST":
        missing = required_fields(
            request.form,
            [
                "username",
                "password",
                "employee_no",
                "full_name",
                "department_id",
            ],
        )

        if missing:
            flash("Complete every teacher field.", "error")
        else:
            connection = get_db()
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO users
                        (username, password_hash, role)
                        VALUES (%s, %s, 'teacher')
                        """,
                        (
                            request.form["username"].strip(),
                            generate_password_hash(request.form["password"]),
                        ),
                    )
                    user_id = cursor.lastrowid

                    cursor.execute(
                        """
                        INSERT INTO teachers
                        (user_id, employee_no, full_name, department_id)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            user_id,
                            request.form["employee_no"].strip().upper(),
                            request.form["full_name"].strip(),
                            request.form["department_id"],
                        ),
                    )

                connection.commit()
                flash("Teacher account created successfully.", "success")
                return redirect(url_for("manage_teachers"))
            except pymysql.err.IntegrityError:
                connection.rollback()
                flash(
                    "Username or employee number already exists.",
                    "error",
                )
            finally:
                connection.close()

    departments = query_all(
        """
        SELECT id, department_code, department_name
        FROM departments
        ORDER BY department_code
        """
    )

    teachers = query_all(
        """
        SELECT
            t.id,
            t.employee_no,
            t.full_name,
            u.username,
            u.is_active,
            d.department_code,
            COUNT(co.id) AS assigned_courses
        FROM teachers t
        JOIN users u ON u.id=t.user_id
        JOIN departments d ON d.id=t.department_id
        LEFT JOIN course_offerings co ON co.teacher_id=t.id
        GROUP BY
            t.id, t.employee_no, t.full_name, u.username,
            u.is_active, d.department_code
        ORDER BY t.full_name
        """
    )

    return render_template(
        "manage_teachers.html",
        departments=departments,
        teachers=teachers,
    )


@app.route("/admin/students", methods=["GET", "POST"])
@login_required("admin")
def manage_students():
    if request.method == "POST":
        missing = required_fields(
            request.form,
            [
                "username",
                "password",
                "register_no",
                "full_name",
                "class_id",
            ],
        )

        if missing:
            flash("Complete every student field.", "error")
        else:
            connection = get_db()
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO users
                        (username, password_hash, role)
                        VALUES (%s, %s, 'student')
                        """,
                        (
                            request.form["username"].strip(),
                            generate_password_hash(request.form["password"]),
                        ),
                    )
                    user_id = cursor.lastrowid

                    cursor.execute(
                        """
                        INSERT INTO students
                        (
                            user_id, register_no, full_name,
                            class_id, face_registered
                        )
                        VALUES (%s, %s, %s, %s, 0)
                        """,
                        (
                            user_id,
                            request.form["register_no"].strip(),
                            request.form["full_name"].strip(),
                            request.form["class_id"],
                        ),
                    )

                connection.commit()
                flash(
                    "Student account created. Face registration is still pending.",
                    "success",
                )
                return redirect(url_for("manage_students"))
            except pymysql.err.IntegrityError:
                connection.rollback()
                flash(
                    "Username or register number already exists.",
                    "error",
                )
            finally:
                connection.close()

    classes = query_all(
        """
        SELECT
            c.id,
            c.class_name,
            c.year_label,
            c.section,
            d.department_code
        FROM classes c
        JOIN departments d ON d.id=c.department_id
        ORDER BY d.department_code, c.year_label, c.section
        """
    )

    students = query_all(
        """
        SELECT
            st.id,
            st.register_no,
            st.full_name,
            st.face_registered,
            u.username,
            c.class_name,
            c.year_label,
            c.section,
            d.department_code,
            COUNT(e.id) AS enrolled_courses
        FROM students st
        LEFT JOIN users u ON u.id=st.user_id
        JOIN classes c ON c.id=st.class_id
        JOIN departments d ON d.id=c.department_id
        LEFT JOIN enrollments e ON e.student_id=st.id
        GROUP BY
            st.id, st.register_no, st.full_name, st.face_registered,
            u.username, c.class_name, c.year_label, c.section,
            d.department_code
        ORDER BY st.register_no
        """
    )

    for student in students:
        student["face_images"] = count_student_images(student["id"])
        student["face_ready"] = student["face_images"] >= 20

    return render_template(
        "manage_students.html",
        classes=classes,
        students=students,
        face_model_exists=model_exists(),
    )


@app.post("/admin/students/<int:student_id>/register-face")
@login_required("admin")
def register_student_face(student_id):
    student = query_one(
        """
        SELECT id, register_no, full_name
        FROM students
        WHERE id=%s
        """,
        (student_id,),
    )

    if not student:
        flash("Student was not found.", "error")
        return redirect(url_for("manage_students"))

    result = capture_student_faces(
        student_id=student["id"],
        student_name=student["full_name"],
        register_no=student["register_no"],
    )

    if result["success"]:
        execute(
            """
            UPDATE students
            SET face_registered=1, face_folder=%s
            WHERE id=%s
            """,
            (f"dataset/User.{student_id}.*.jpg", student_id),
        )
        flash(
            result["message"] + " Train the face model after registrations.",
            "success",
        )
    else:
        execute(
            "UPDATE students SET face_registered=0 WHERE id=%s",
            (student_id,),
        )
        flash(result["message"], "error")

    return redirect(url_for("manage_students"))


@app.post("/admin/train-face-model")
@login_required("admin")
def train_model_web():
    result = train_face_model()
    flash(result["message"], "success" if result["success"] else "error")
    return redirect(url_for("manage_students"))


@app.route("/admin/offerings", methods=["GET", "POST"])
@login_required("admin")
def manage_offerings():
    if request.method == "POST":
        missing = required_fields(
            request.form,
            [
                "subject_id",
                "class_id",
                "slot_id",
                "teacher_id",
                "academic_year",
                "semester",
            ],
        )

        if missing:
            flash("Complete every course-assignment field.", "error")
        else:
            try:
                offering_id = execute(
                    """
                    INSERT INTO course_offerings
                    (
                        subject_id,
                        class_id,
                        slot_id,
                        teacher_id,
                        academic_year,
                        semester,
                        room_name
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        request.form["subject_id"],
                        request.form["class_id"],
                        request.form["slot_id"],
                        request.form["teacher_id"],
                        request.form["academic_year"].strip(),
                        request.form["semester"].strip(),
                        request.form.get("room_name", "").strip() or None,
                    ),
                )

                created = sync_offering_slot_schedules(offering_id)

                flash(
                    "Course assignment created. "
                    f"{created} master-slot timetable row(s) were added automatically.",
                    "success",
                )
                return redirect(url_for("manage_offerings"))

            except pymysql.err.IntegrityError:
                flash("That course assignment already exists.", "error")

    subjects = query_all(
        """
        SELECT id, subject_code, subject_name
        FROM subjects
        ORDER BY subject_code
        """
    )

    classes = query_all(
        """
        SELECT
            c.id,
            c.class_name,
            c.year_label,
            c.section,
            d.department_code
        FROM classes c
        JOIN departments d ON d.id=c.department_id
        ORDER BY d.department_code, c.year_label, c.section
        """
    )

    slots = query_all(
        """
        SELECT id, slot_code, slot_name
        FROM slots
        ORDER BY slot_code
        """
    )

    teachers = query_all(
        """
        SELECT id, employee_no, full_name
        FROM teachers
        ORDER BY full_name
        """
    )

    offerings = query_all(
        """
        SELECT
            co.id,
            co.room_name,
            s.subject_code,
            s.subject_name,
            sl.slot_name,
            t.full_name AS teacher_name,
            c.class_name,
            c.year_label,
            c.section,
            co.academic_year,
            co.semester,
            COUNT(DISTINCT e.id) AS student_count,
            COUNT(DISTINCT tt.id) AS timetable_count
        FROM course_offerings co
        JOIN subjects s ON s.id=co.subject_id
        JOIN slots sl ON sl.id=co.slot_id
        JOIN teachers t ON t.id=co.teacher_id
        JOIN classes c ON c.id=co.class_id
        LEFT JOIN enrollments e ON e.offering_id=co.id
        LEFT JOIN timetable_entries tt ON tt.offering_id=co.id
        WHERE co.is_active=1
        GROUP BY
            co.id,
            co.room_name,
            s.subject_code,
            s.subject_name,
            sl.slot_name,
            t.full_name,
            c.class_name,
            c.year_label,
            c.section,
            co.academic_year,
            co.semester
        ORDER BY s.subject_code, c.section
        """
    )

    return render_template(
        "manage_offerings.html",
        subjects=subjects,
        classes=classes,
        slots=slots,
        teachers=teachers,
        offerings=offerings,
    )


@app.post("/admin/offerings/<int:offering_id>/room")
@login_required("admin")
def update_offering_room(offering_id):
    room_name = request.form.get("room_name", "").strip() or None

    connection = get_db()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE course_offerings
                SET room_name=%s
                WHERE id=%s
                """,
                (room_name, offering_id),
            )

            cursor.execute(
                """
                UPDATE timetable_entries
                SET room_name=%s
                WHERE offering_id=%s
                """,
                (room_name, offering_id),
            )

        connection.commit()
        flash("Course room updated successfully.", "success")

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return redirect(url_for("manage_offerings"))


@app.route("/admin/enrollments", methods=["GET", "POST"])
@login_required("admin")
def manage_enrollments():
    if request.method == "POST":
        action = request.form.get("action", "single")
        offering_id = request.form.get("offering_id", "").strip()

        if not offering_id:
            flash("Select a course offering.", "error")
        elif action == "bulk":
            offering = query_one(
                "SELECT class_id FROM course_offerings WHERE id=%s",
                (offering_id,),
            )

            if not offering:
                flash("Course offering was not found.", "error")
            else:
                connection = get_db()
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            INSERT IGNORE INTO enrollments
                            (offering_id, student_id)
                            SELECT %s, id
                            FROM students
                            WHERE class_id=%s
                            """,
                            (offering_id, offering["class_id"]),
                        )
                        added = cursor.rowcount
                    connection.commit()
                    flash(
                        f"Class students enrolled. New enrolments: {added}.",
                        "success",
                    )
                    return redirect(url_for("manage_enrollments"))
                except Exception:
                    connection.rollback()
                    raise
                finally:
                    connection.close()
        else:
            student_id = request.form.get("student_id", "").strip()

            if not student_id:
                flash("Select a student.", "error")
            else:
                try:
                    execute(
                        """
                        INSERT INTO enrollments (offering_id, student_id)
                        VALUES (%s, %s)
                        """,
                        (offering_id, student_id),
                    )
                    flash("Student enrolled successfully.", "success")
                    return redirect(url_for("manage_enrollments"))
                except pymysql.err.IntegrityError:
                    flash(
                        "The student is already enrolled in that course.",
                        "error",
                    )

    offerings = query_all(
        """
        SELECT
            co.id,
            s.subject_code,
            s.subject_name,
            sl.slot_name,
            c.class_name,
            c.year_label,
            c.section,
            COUNT(e.id) AS student_count
        FROM course_offerings co
        JOIN subjects s ON s.id=co.subject_id
        JOIN slots sl ON sl.id=co.slot_id
        JOIN classes c ON c.id=co.class_id
        LEFT JOIN enrollments e ON e.offering_id=co.id
        WHERE co.is_active=1
        GROUP BY
            co.id, s.subject_code, s.subject_name, sl.slot_name,
            c.class_name, c.year_label, c.section
        ORDER BY s.subject_code
        """
    )

    students = query_all(
        """
        SELECT
            st.id,
            st.register_no,
            st.full_name,
            c.year_label,
            c.section
        FROM students st
        JOIN classes c ON c.id=st.class_id
        ORDER BY st.register_no
        """
    )

    recent = query_all(
        """
        SELECT
            e.id,
            st.register_no,
            st.full_name,
            s.subject_code,
            sl.slot_name
        FROM enrollments e
        JOIN students st ON st.id=e.student_id
        JOIN course_offerings co ON co.id=e.offering_id
        JOIN subjects s ON s.id=co.subject_id
        JOIN slots sl ON sl.id=co.slot_id
        ORDER BY e.id DESC
        LIMIT 50
        """
    )

    return render_template(
        "manage_enrollments.html",
        offerings=offerings,
        students=students,
        recent=recent,
    )


@app.route("/admin/timetable", methods=["GET", "POST"])
@login_required("admin")
def manage_timetable():
    if request.method == "POST":
        missing = required_fields(
            request.form,
            ["slot_id", "day_of_week", "start_time", "end_time"],
        )

        if missing:
            flash("Complete the slot, day and timing fields.", "error")

        elif request.form["start_time"] >= request.form["end_time"]:
            flash("End time must be later than start time.", "error")

        else:
            try:
                schedule_id = execute(
                    """
                    INSERT INTO slot_schedules
                    (slot_id, day_of_week, start_time, end_time)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        request.form["slot_id"],
                        request.form["day_of_week"],
                        request.form["start_time"],
                        request.form["end_time"],
                    ),
                )

                created = sync_slot_schedule(schedule_id)

                flash(
                    "Master slot timing added. "
                    f"It was applied to {created} course timetable row(s).",
                    "success",
                )
                return redirect(url_for("manage_timetable"))

            except pymysql.err.IntegrityError:
                flash(
                    "That slot already has the same day and timing.",
                    "error",
                )

    slots = query_all(
        """
        SELECT id, slot_code, slot_name
        FROM slots
        ORDER BY slot_code
        """
    )

    master_schedules = query_all(
        """
        SELECT
            ss.id,
            ss.day_of_week,
            ss.start_time,
            ss.end_time,
            sl.slot_code,
            sl.slot_name,
            COUNT(DISTINCT co.id) AS course_count,
            COUNT(DISTINCT tt.id) AS applied_count
        FROM slot_schedules ss
        JOIN slots sl ON sl.id=ss.slot_id
        LEFT JOIN course_offerings co
          ON co.slot_id=ss.slot_id
         AND co.is_active=1
        LEFT JOIN timetable_entries tt
          ON tt.slot_schedule_id=ss.id
        GROUP BY
            ss.id,
            ss.day_of_week,
            ss.start_time,
            ss.end_time,
            sl.slot_code,
            sl.slot_name
        ORDER BY
            sl.slot_code,
            ss.day_of_week,
            ss.start_time
        """
    )

    timetable = query_all(
        """
        SELECT
            tt.id,
            tt.slot_schedule_id,
            tt.day_of_week,
            tt.start_time,
            tt.end_time,
            tt.room_name,
            s.subject_code,
            s.subject_name,
            sl.slot_name,
            t.full_name AS teacher_name,
            c.year_label,
            c.section,
            EXISTS(
                SELECT 1
                FROM attendance_sessions ats
                WHERE ats.timetable_entry_id=tt.id
            ) AS has_attendance
        FROM timetable_entries tt
        JOIN course_offerings co ON co.id=tt.offering_id
        JOIN subjects s ON s.id=co.subject_id
        JOIN slots sl ON sl.id=co.slot_id
        JOIN teachers t ON t.id=co.teacher_id
        JOIN classes c ON c.id=co.class_id
        ORDER BY
            tt.day_of_week,
            tt.start_time,
            sl.slot_name,
            s.subject_code
        """
    )

    weekly = {index: [] for index in range(7)}

    for item in master_schedules:
        weekly[item["day_of_week"]].append(item)

    return render_template(
        "manage_timetable.html",
        slots=slots,
        master_schedules=master_schedules,
        timetable=timetable,
        weekly=weekly,
    )


@app.post("/admin/timetable/sync")
@login_required("admin")
def sync_master_timetable():
    created = sync_all_slot_schedules()

    flash(
        f"Master slot timetable synchronized. "
        f"{created} missing course timetable row(s) were created.",
        "success",
    )
    return redirect(url_for("manage_timetable"))


@app.route(
    "/admin/timetable/master/<int:schedule_id>/edit",
    methods=["GET", "POST"],
)
@login_required("admin")
def edit_slot_schedule(schedule_id):
    schedule = query_one(
        """
        SELECT
            ss.id,
            ss.slot_id,
            ss.day_of_week,
            ss.start_time,
            ss.end_time,
            sl.slot_code,
            sl.slot_name
        FROM slot_schedules ss
        JOIN slots sl ON sl.id=ss.slot_id
        WHERE ss.id=%s
        """,
        (schedule_id,),
    )

    if not schedule:
        flash("Master slot timing was not found.", "error")
        return redirect(url_for("manage_timetable"))

    if request.method == "POST":
        missing = required_fields(
            request.form,
            ["slot_id", "day_of_week", "start_time", "end_time"],
        )

        if missing:
            flash("Complete every timing field.", "error")

        elif request.form["start_time"] >= request.form["end_time"]:
            flash("End time must be later than start time.", "error")

        else:
            connection = get_db()

            try:
                with connection.cursor() as cursor:
                    # Keep timetable rows that already have attendance history.
                    cursor.execute(
                        """
                        UPDATE timetable_entries tt
                        SET tt.slot_schedule_id=NULL
                        WHERE tt.slot_schedule_id=%s
                          AND EXISTS(
                              SELECT 1
                              FROM attendance_sessions ats
                              WHERE ats.timetable_entry_id=tt.id
                          )
                        """,
                        (schedule_id,),
                    )

                    # Remove unused generated rows before applying new timing.
                    cursor.execute(
                        """
                        DELETE tt
                        FROM timetable_entries tt
                        LEFT JOIN attendance_sessions ats
                          ON ats.timetable_entry_id=tt.id
                        WHERE tt.slot_schedule_id=%s
                          AND ats.id IS NULL
                        """,
                        (schedule_id,),
                    )

                    cursor.execute(
                        """
                        UPDATE slot_schedules
                        SET
                            slot_id=%s,
                            day_of_week=%s,
                            start_time=%s,
                            end_time=%s
                        WHERE id=%s
                        """,
                        (
                            request.form["slot_id"],
                            request.form["day_of_week"],
                            request.form["start_time"],
                            request.form["end_time"],
                            schedule_id,
                        ),
                    )

                connection.commit()
                created = sync_slot_schedule(schedule_id)

                flash(
                    "Master slot timing updated. "
                    f"{created} course timetable row(s) were regenerated.",
                    "success",
                )
                return redirect(url_for("manage_timetable"))

            except pymysql.err.IntegrityError:
                connection.rollback()
                flash(
                    "Another master timing already uses those same details.",
                    "error",
                )
            finally:
                connection.close()

    slots = query_all(
        """
        SELECT id, slot_code, slot_name
        FROM slots
        ORDER BY slot_code
        """
    )

    return render_template(
        "edit_slot_schedule.html",
        schedule=schedule,
        slots=slots,
    )


@app.post("/admin/timetable/master/<int:schedule_id>/delete")
@login_required("admin")
def delete_slot_schedule(schedule_id):
    connection = get_db()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM slot_schedules
                WHERE id=%s
                """,
                (schedule_id,),
            )

            if not cursor.fetchone():
                flash("Master slot timing was not found.", "error")
                return redirect(url_for("manage_timetable"))

            # Preserve rules already used by submitted/draft attendance history.
            cursor.execute(
                """
                UPDATE timetable_entries tt
                SET tt.slot_schedule_id=NULL
                WHERE tt.slot_schedule_id=%s
                  AND EXISTS(
                      SELECT 1
                      FROM attendance_sessions ats
                      WHERE ats.timetable_entry_id=tt.id
                  )
                """,
                (schedule_id,),
            )

            # Delete generated rows that have never been used.
            cursor.execute(
                """
                DELETE tt
                FROM timetable_entries tt
                LEFT JOIN attendance_sessions ats
                  ON ats.timetable_entry_id=tt.id
                WHERE tt.slot_schedule_id=%s
                  AND ats.id IS NULL
                """,
                (schedule_id,),
            )

            cursor.execute(
                "DELETE FROM slot_schedules WHERE id=%s",
                (schedule_id,),
            )

        connection.commit()
        flash(
            "Master slot timing deleted. Existing attendance history was preserved.",
            "success",
        )

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return redirect(url_for("manage_timetable"))


@app.post("/admin/timetable/entry/<int:entry_id>/delete")
@login_required("admin")
def delete_timetable_entry(entry_id):
    used = query_one(
        """
        SELECT COUNT(*) AS total
        FROM attendance_sessions
        WHERE timetable_entry_id=%s
        """,
        (entry_id,),
    )

    if used and used["total"] > 0:
        flash(
            "This timetable row already has attendance history and cannot be deleted.",
            "error",
        )
        return redirect(url_for("manage_timetable"))

    execute(
        "DELETE FROM timetable_entries WHERE id=%s",
        (entry_id,),
    )

    flash("Unused timetable row deleted.", "success")
    return redirect(url_for("manage_timetable"))


# -------------------------------------------------------------------
# TEACHER ATTENDANCE
# -------------------------------------------------------------------

@app.route("/teacher")
@login_required("teacher")
def teacher_dashboard():
    teacher = query_one(
        """
        SELECT t.id, t.full_name
        FROM teachers t
        WHERE t.user_id=%s
        """,
        (session["user_id"],),
    )

    if not teacher:
        flash("Teacher profile is not linked to this account.", "error")
        return redirect(url_for("logout"))

    weekday = date.today().weekday()

    todays_classes = query_all(
        """
        SELECT
            tt.id AS timetable_id,
            co.id AS offering_id,
            s.subject_code,
            s.subject_name,
            sl.slot_code,
            sl.slot_name,
            c.class_name,
            c.year_label,
            c.section,
            tt.start_time,
            tt.end_time,
            tt.room_name,
            ats.id AS session_id,
            ats.status AS session_status
        FROM timetable_entries tt
        JOIN course_offerings co ON co.id=tt.offering_id
        JOIN subjects s ON s.id=co.subject_id
        JOIN slots sl ON sl.id=co.slot_id
        JOIN classes c ON c.id=co.class_id
        LEFT JOIN attendance_sessions ats
            ON ats.timetable_entry_id=tt.id
            AND ats.session_date=%s
        WHERE co.teacher_id=%s
            AND co.is_active=1
            AND tt.day_of_week=%s
        ORDER BY tt.start_time
        """,
        (date.today(), teacher["id"], weekday),
    )

    assigned_courses = query_all(
        """
        SELECT
            co.id,
            s.subject_code,
            s.subject_name,
            sl.slot_name,
            c.class_name,
            c.year_label,
            c.section,
            COUNT(e.id) AS student_count
        FROM course_offerings co
        JOIN subjects s ON s.id=co.subject_id
        JOIN slots sl ON sl.id=co.slot_id
        JOIN classes c ON c.id=co.class_id
        LEFT JOIN enrollments e ON e.offering_id=co.id
        WHERE co.teacher_id=%s AND co.is_active=1
        GROUP BY
            co.id, s.subject_code, s.subject_name, sl.slot_name,
            c.class_name, c.year_label, c.section
        ORDER BY s.subject_name
        """,
        (teacher["id"],),
    )

    return render_template(
        "teacher_dashboard.html",
        teacher=teacher,
        todays_classes=todays_classes,
        assigned_courses=assigned_courses,
        today=date.today(),
    )


@app.post("/teacher/session/start/<int:timetable_id>")
@login_required("teacher")
def start_attendance(timetable_id):
    teacher = query_one(
        "SELECT id FROM teachers WHERE user_id=%s",
        (session["user_id"],),
    )

    timetable = query_one(
        """
        SELECT tt.*, co.teacher_id
        FROM timetable_entries tt
        JOIN course_offerings co ON co.id=tt.offering_id
        WHERE tt.id=%s
        """,
        (timetable_id,),
    )

    if not timetable or timetable["teacher_id"] != teacher["id"]:
        flash("You cannot start this attendance session.", "error")
        return redirect(url_for("teacher_dashboard"))

    existing = query_one(
        """
        SELECT id FROM attendance_sessions
        WHERE timetable_entry_id=%s AND session_date=%s
        """,
        (timetable_id, date.today()),
    )

    if existing:
        return redirect(
            url_for("attendance_session", session_id=existing["id"])
        )

    opened_at = datetime.now()
    closes_at = opened_at + timedelta(minutes=10)

    session_id = execute(
        """
        INSERT INTO attendance_sessions
        (
            offering_id, timetable_entry_id, session_date,
            attendance_opened_at, attendance_closes_at,
            status, created_by
        )
        VALUES (%s, %s, %s, %s, %s, 'draft', %s)
        """,
        (
            timetable["offering_id"],
            timetable_id,
            date.today(),
            opened_at,
            closes_at,
            session["user_id"],
        ),
    )

    enrolled_students = query_all(
        """
        SELECT student_id
        FROM enrollments
        WHERE offering_id=%s
        """,
        (timetable["offering_id"],),
    )

    connection = get_db()
    try:
        with connection.cursor() as cursor:
            for row in enrolled_students:
                cursor.execute(
                    """
                    INSERT IGNORE INTO attendance_records
                    (session_id, student_id, status, method)
                    VALUES (%s, %s, 'pending', 'automatic')
                    """,
                    (session_id, row["student_id"]),
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    flash("Attendance started. It is saved as Draft.", "success")
    return redirect(url_for("attendance_session", session_id=session_id))


@app.route("/teacher/session/<int:session_id>")
@login_required("teacher")
def attendance_session(session_id):
    attendance = query_one(
        """
        SELECT
            ats.*,
            s.subject_code,
            s.subject_name,
            sl.slot_name,
            c.class_name,
            c.year_label,
            c.section,
            t.full_name AS teacher_name
        FROM attendance_sessions ats
        JOIN course_offerings co ON co.id=ats.offering_id
        JOIN subjects s ON s.id=co.subject_id
        JOIN slots sl ON sl.id=co.slot_id
        JOIN classes c ON c.id=co.class_id
        JOIN teachers t ON t.id=co.teacher_id
        WHERE ats.id=%s AND t.user_id=%s
        """,
        (session_id, session["user_id"]),
    )

    if not attendance:
        flash("Attendance session was not found.", "error")
        return redirect(url_for("teacher_dashboard"))

    records = query_all(
        """
        SELECT
            ar.student_id,
            st.register_no,
            st.full_name,
            ar.status,
            ar.method,
            ar.reason,
            ar.marked_at
        FROM attendance_records ar
        JOIN students st ON st.id=ar.student_id
        WHERE ar.session_id=%s
        ORDER BY st.register_no
        """,
        (session_id,),
    )

    summary = {
        "present": 0,
        "permission": 0,
        "absent": 0,
        "pending": 0,
    }

    for record in records:
        if record["status"] == "present":
            summary["present"] += 1
        elif record["status"] == "present_permission":
            summary["permission"] += 1
        elif record["status"] == "absent":
            summary["absent"] += 1
        else:
            summary["pending"] += 1

    face_ready_count = sum(
        1 for record in records
        if count_student_images(record["student_id"]) >= 20
    )

    return render_template(
        "attendance_session.html",
        attendance=attendance,
        records=records,
        summary=summary,
        now=datetime.now(),
        face_model_exists=model_exists(),
        face_ready_count=face_ready_count,
    )


@app.post("/teacher/session/<int:session_id>/recognize-faces")
@login_required("teacher")
def recognize_session_faces(session_id):
    attendance = query_one(
        """
        SELECT
            ats.id, ats.status, ats.offering_id, t.user_id
        FROM attendance_sessions ats
        JOIN course_offerings co ON co.id=ats.offering_id
        JOIN teachers t ON t.id=co.teacher_id
        WHERE ats.id=%s
        """,
        (session_id,),
    )

    if not attendance or attendance["user_id"] != session["user_id"]:
        flash("Attendance session was not found.", "error")
        return redirect(url_for("teacher_dashboard"))

    if attendance["status"] != "draft":
        flash("Only Draft attendance can use face verification.", "error")
        return redirect(url_for("attendance_session", session_id=session_id))

    if not model_exists():
        flash("Face model is not trained. Ask Admin to train the model.", "error")
        return redirect(url_for("attendance_session", session_id=session_id))

    enrolled = query_all(
        """
        SELECT st.id, st.register_no, st.full_name
        FROM attendance_records ar
        JOIN students st ON st.id=ar.student_id
        WHERE ar.session_id=%s
        ORDER BY st.register_no
        """,
        (session_id,),
    )

    eligible_students = {
        row["id"]: row
        for row in enrolled
        if count_student_images(row["id"]) >= 20
    }

    if not eligible_students:
        flash(
            "No enrolled students have enough captured face images.",
            "error",
        )
        return redirect(url_for("attendance_session", session_id=session_id))

    opened_at = datetime.now()
    closes_at = opened_at + timedelta(minutes=10)
    execute(
        """
        UPDATE attendance_sessions
        SET attendance_opened_at=%s, attendance_closes_at=%s
        WHERE id=%s
        """,
        (opened_at, closes_at, session_id),
    )

    result = recognize_enrolled_students(
        eligible_students=eligible_students,
        max_seconds=600,
    )

    if result["success"] and result["recognized_ids"]:
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                for student_id in result["recognized_ids"]:
                    cursor.execute(
                        """
                        UPDATE attendance_records
                        SET status='present',
                            method='face_recognition',
                            reason=NULL,
                            marked_by=%s,
                            marked_at=NOW()
                        WHERE session_id=%s
                            AND student_id=%s
                            AND status IN ('pending', 'present')
                        """,
                        (session["user_id"], session_id, student_id),
                    )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    flash(
        result["message"],
        "success" if result["success"] else "error",
    )
    return redirect(url_for("attendance_session", session_id=session_id))


@app.post("/teacher/session/<int:session_id>/face/<int:student_id>")
@login_required("teacher")
def mark_face(session_id, student_id):
    attendance = query_one(
        """
        SELECT ats.status, t.user_id
        FROM attendance_sessions ats
        JOIN course_offerings co ON co.id=ats.offering_id
        JOIN teachers t ON t.id=co.teacher_id
        WHERE ats.id=%s
        """,
        (session_id,),
    )

    if not attendance or attendance["user_id"] != session["user_id"]:
        flash("Attendance session was not found.", "error")
        return redirect(url_for("teacher_dashboard"))

    if attendance["status"] != "draft":
        flash("Submitted or cancelled attendance cannot be changed.", "error")
        return redirect(url_for("attendance_session", session_id=session_id))

    execute(
        """
        UPDATE attendance_records
        SET status='present',
            method='face_recognition',
            reason=NULL,
            marked_by=%s,
            marked_at=NOW()
        WHERE session_id=%s AND student_id=%s
        """,
        (session["user_id"], session_id, student_id),
    )

    flash("Face attendance marked for testing.", "success")
    return redirect(url_for("attendance_session", session_id=session_id))


@app.post("/teacher/session/<int:session_id>/permission/<int:student_id>")
@login_required("teacher")
def mark_permission(session_id, student_id):
    reason = request.form.get("reason", "").strip()

    if not reason:
        flash("Permission reason is required.", "error")
        return redirect(url_for("attendance_session", session_id=session_id))

    attendance = query_one(
        """
        SELECT ats.status, t.user_id
        FROM attendance_sessions ats
        JOIN course_offerings co ON co.id=ats.offering_id
        JOIN teachers t ON t.id=co.teacher_id
        WHERE ats.id=%s
        """,
        (session_id,),
    )

    if not attendance or attendance["user_id"] != session["user_id"]:
        flash("Attendance session was not found.", "error")
        return redirect(url_for("teacher_dashboard"))

    if attendance["status"] != "draft":
        flash("Submitted or cancelled attendance cannot be changed.", "error")
        return redirect(url_for("attendance_session", session_id=session_id))

    execute(
        """
        UPDATE attendance_records
        SET status='present_permission',
            method='teacher_permission',
            reason=%s,
            marked_by=%s,
            marked_at=NOW()
        WHERE session_id=%s AND student_id=%s
        """,
        (reason, session["user_id"], session_id, student_id),
    )

    flash("Permission attendance saved with the reason.", "success")
    return redirect(url_for("attendance_session", session_id=session_id))


@app.post("/teacher/session/<int:session_id>/submit")
@login_required("teacher")
def submit_attendance(session_id):
    attendance = query_one(
        """
        SELECT ats.status, t.user_id
        FROM attendance_sessions ats
        JOIN course_offerings co ON co.id=ats.offering_id
        JOIN teachers t ON t.id=co.teacher_id
        WHERE ats.id=%s
        """,
        (session_id,),
    )

    if not attendance or attendance["user_id"] != session["user_id"]:
        flash("Attendance session was not found.", "error")
        return redirect(url_for("teacher_dashboard"))

    if attendance["status"] != "draft":
        flash("Only Draft attendance can be submitted.", "error")
        return redirect(url_for("attendance_session", session_id=session_id))

    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE attendance_records
                SET status='absent',
                    method='automatic',
                    marked_at=NOW()
                WHERE session_id=%s AND status='pending'
                """,
                (session_id,),
            )

            cursor.execute(
                """
                UPDATE attendance_sessions
                SET status='submitted', submitted_at=NOW()
                WHERE id=%s
                """,
                (session_id,),
            )

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    flash(
        "Attendance submitted. Present, permission and absent are now final.",
        "success",
    )
    return redirect(url_for("attendance_session", session_id=session_id))


@app.post("/teacher/session/<int:session_id>/cancel")
@login_required("teacher")
def cancel_attendance(session_id):
    reason = request.form.get("reason", "").strip()

    if not reason:
        flash("Cancellation reason is required.", "error")
        return redirect(url_for("attendance_session", session_id=session_id))

    attendance = query_one(
        """
        SELECT ats.status, t.user_id
        FROM attendance_sessions ats
        JOIN course_offerings co ON co.id=ats.offering_id
        JOIN teachers t ON t.id=co.teacher_id
        WHERE ats.id=%s
        """,
        (session_id,),
    )

    if not attendance or attendance["user_id"] != session["user_id"]:
        flash("Attendance session was not found.", "error")
        return redirect(url_for("teacher_dashboard"))

    if attendance["status"] != "draft":
        flash("Only Draft attendance can be cancelled.", "error")
        return redirect(url_for("attendance_session", session_id=session_id))

    execute(
        """
        UPDATE attendance_sessions
        SET status='cancelled', cancel_reason=%s
        WHERE id=%s
        """,
        (reason, session_id),
    )

    flash("Class cancelled. It will not affect attendance percentage.", "success")
    return redirect(url_for("attendance_session", session_id=session_id))



# -------------------------------------------------------------------
# ATTENDANCE REPORTS
# -------------------------------------------------------------------

@app.route("/reports")
@login_required()
def attendance_reports():
    if session.get("role") not in {"admin", "teacher"}:
        flash("Reports are available to Admin and Teachers.", "error")
        return redirect(url_for("dashboard"))

    role = session["role"]
    teacher_id = None

    if role == "teacher":
        teacher = query_one(
            "SELECT id FROM teachers WHERE user_id=%s",
            (session["user_id"],),
        )
        if not teacher:
            flash("Teacher profile is not linked to this account.", "error")
            return redirect(url_for("dashboard"))
        teacher_id = teacher["id"]

    offering_id = request.args.get("offering_id", "").strip()
    class_id = request.args.get("class_id", "").strip()
    student_id = request.args.get("student_id", "").strip()
    record_status = request.args.get("record_status", "").strip()
    session_status = request.args.get("session_status", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    where = ["1=1"]
    args = []

    if teacher_id:
        where.append("co.teacher_id=%s")
        args.append(teacher_id)
    if offering_id:
        where.append("co.id=%s")
        args.append(offering_id)
    if class_id:
        where.append("co.class_id=%s")
        args.append(class_id)
    if student_id:
        where.append("st.id=%s")
        args.append(student_id)
    if record_status:
        where.append("ar.status=%s")
        args.append(record_status)
    if session_status:
        where.append("ats.status=%s")
        args.append(session_status)
    if date_from:
        where.append("ats.session_date >= %s")
        args.append(date_from)
    if date_to:
        where.append("ats.session_date <= %s")
        args.append(date_to)

    where_sql = " AND ".join(where)

    records = query_all(
        f"""
        SELECT
            ar.id,
            ats.id AS session_id,
            ats.session_date,
            ats.status AS session_status,
            ats.submitted_at,
            s.subject_code,
            s.subject_name,
            sl.slot_name,
            t.full_name AS teacher_name,
            c.class_name,
            c.year_label,
            c.section,
            st.id AS student_id,
            st.register_no,
            st.full_name AS student_name,
            ar.status AS attendance_status,
            ar.method,
            ar.reason,
            ar.marked_at
        FROM attendance_records ar
        JOIN attendance_sessions ats ON ats.id=ar.session_id
        JOIN course_offerings co ON co.id=ats.offering_id
        JOIN subjects s ON s.id=co.subject_id
        JOIN slots sl ON sl.id=co.slot_id
        JOIN teachers t ON t.id=co.teacher_id
        JOIN classes c ON c.id=co.class_id
        JOIN students st ON st.id=ar.student_id
        WHERE {where_sql}
        ORDER BY ats.session_date DESC, s.subject_code, st.register_no
        LIMIT 1000
        """,
        tuple(args),
    )

    summary = {
        "records": len(records),
        "present": 0,
        "permission": 0,
        "absent": 0,
        "pending": 0,
    }
    for row in records:
        status = row["attendance_status"]
        if status == "present":
            summary["present"] += 1
        elif status == "present_permission":
            summary["permission"] += 1
        elif status == "absent":
            summary["absent"] += 1
        else:
            summary["pending"] += 1

    # Course totals use only submitted attendance records.
    course_where = ["ats.status='submitted'"]
    course_args = []
    if teacher_id:
        course_where.append("co.teacher_id=%s")
        course_args.append(teacher_id)
    if offering_id:
        course_where.append("co.id=%s")
        course_args.append(offering_id)
    if class_id:
        course_where.append("co.class_id=%s")
        course_args.append(class_id)
    if date_from:
        course_where.append("ats.session_date >= %s")
        course_args.append(date_from)
    if date_to:
        course_where.append("ats.session_date <= %s")
        course_args.append(date_to)

    course_summaries = query_all(
        f"""
        SELECT
            co.id AS offering_id,
            s.subject_code,
            s.subject_name,
            sl.slot_name,
            t.full_name AS teacher_name,
            c.class_name,
            c.year_label,
            c.section,
            COUNT(DISTINCT ats.id) AS conducted_sessions,
            SUM(CASE WHEN ar.status='present' THEN 1 ELSE 0 END) AS face_present,
            SUM(CASE WHEN ar.status='present_permission' THEN 1 ELSE 0 END) AS permission_present,
            SUM(CASE WHEN ar.status='absent' THEN 1 ELSE 0 END) AS absent_records,
            COUNT(ar.id) AS total_records
        FROM course_offerings co
        JOIN subjects s ON s.id=co.subject_id
        JOIN slots sl ON sl.id=co.slot_id
        JOIN teachers t ON t.id=co.teacher_id
        JOIN classes c ON c.id=co.class_id
        LEFT JOIN attendance_sessions ats ON ats.offering_id=co.id
        LEFT JOIN attendance_records ar ON ar.session_id=ats.id
        WHERE {' AND '.join(course_where)}
        GROUP BY
            co.id, s.subject_code, s.subject_name, sl.slot_name,
            t.full_name, c.class_name, c.year_label, c.section
        ORDER BY s.subject_code
        """,
        tuple(course_args),
    )

    for row in course_summaries:
        attended = int(row["face_present"] or 0) + int(row["permission_present"] or 0)
        total = int(row["total_records"] or 0)
        row["attendance_percentage"] = round(attended / total * 100, 2) if total else 0

    # Student/subject percentage table.
    student_where = ["ats.status='submitted'"]
    student_args = []
    if teacher_id:
        student_where.append("co.teacher_id=%s")
        student_args.append(teacher_id)
    if offering_id:
        student_where.append("co.id=%s")
        student_args.append(offering_id)
    if class_id:
        student_where.append("co.class_id=%s")
        student_args.append(class_id)
    if student_id:
        student_where.append("st.id=%s")
        student_args.append(student_id)
    if date_from:
        student_where.append("ats.session_date >= %s")
        student_args.append(date_from)
    if date_to:
        student_where.append("ats.session_date <= %s")
        student_args.append(date_to)

    student_summaries = query_all(
        f"""
        SELECT
            st.id AS student_id,
            st.register_no,
            st.full_name AS student_name,
            s.subject_code,
            s.subject_name,
            sl.slot_name,
            c.year_label,
            c.section,
            COUNT(ar.id) AS conducted,
            SUM(CASE WHEN ar.status IN ('present', 'present_permission') THEN 1 ELSE 0 END) AS attended,
            SUM(CASE WHEN ar.status='absent' THEN 1 ELSE 0 END) AS absent,
            SUM(CASE WHEN ar.status='present_permission' THEN 1 ELSE 0 END) AS permission_count
        FROM attendance_records ar
        JOIN attendance_sessions ats ON ats.id=ar.session_id
        JOIN course_offerings co ON co.id=ats.offering_id
        JOIN subjects s ON s.id=co.subject_id
        JOIN slots sl ON sl.id=co.slot_id
        JOIN classes c ON c.id=co.class_id
        JOIN students st ON st.id=ar.student_id
        WHERE {' AND '.join(student_where)}
        GROUP BY
            st.id, st.register_no, st.full_name,
            s.subject_code, s.subject_name, sl.slot_name,
            c.year_label, c.section
        ORDER BY st.register_no, s.subject_code
        LIMIT 1000
        """,
        tuple(student_args),
    )

    for row in student_summaries:
        conducted = int(row["conducted"] or 0)
        attended = int(row["attended"] or 0)
        row["percentage"] = round(attended / conducted * 100, 2) if conducted else 0

    session_where = ["1=1"]
    session_args = []
    if teacher_id:
        session_where.append("co.teacher_id=%s")
        session_args.append(teacher_id)
    if offering_id:
        session_where.append("co.id=%s")
        session_args.append(offering_id)
    if class_id:
        session_where.append("co.class_id=%s")
        session_args.append(class_id)
    if session_status:
        session_where.append("ats.status=%s")
        session_args.append(session_status)
    if date_from:
        session_where.append("ats.session_date >= %s")
        session_args.append(date_from)
    if date_to:
        session_where.append("ats.session_date <= %s")
        session_args.append(date_to)

    session_history = query_all(
        f"""
        SELECT
            ats.id,
            ats.session_date,
            ats.status,
            ats.attendance_opened_at,
            ats.submitted_at,
            ats.cancel_reason,
            s.subject_code,
            s.subject_name,
            sl.slot_name,
            t.full_name AS teacher_name,
            c.year_label,
            c.section,
            SUM(CASE WHEN ar.status='present' THEN 1 ELSE 0 END) AS face_present,
            SUM(CASE WHEN ar.status='present_permission' THEN 1 ELSE 0 END) AS permission_present,
            SUM(CASE WHEN ar.status='absent' THEN 1 ELSE 0 END) AS absent_count,
            SUM(CASE WHEN ar.status='pending' THEN 1 ELSE 0 END) AS pending_count
        FROM attendance_sessions ats
        JOIN course_offerings co ON co.id=ats.offering_id
        JOIN subjects s ON s.id=co.subject_id
        JOIN slots sl ON sl.id=co.slot_id
        JOIN teachers t ON t.id=co.teacher_id
        JOIN classes c ON c.id=co.class_id
        LEFT JOIN attendance_records ar ON ar.session_id=ats.id
        WHERE {' AND '.join(session_where)}
        GROUP BY
            ats.id, ats.session_date, ats.status,
            ats.attendance_opened_at, ats.submitted_at, ats.cancel_reason,
            s.subject_code, s.subject_name, sl.slot_name,
            t.full_name, c.year_label, c.section
        ORDER BY ats.session_date DESC, ats.id DESC
        LIMIT 300
        """,
        tuple(session_args),
    )

    offering_sql = """
        SELECT
            co.id,
            s.subject_code,
            s.subject_name,
            sl.slot_name,
            c.year_label,
            c.section
        FROM course_offerings co
        JOIN subjects s ON s.id=co.subject_id
        JOIN slots sl ON sl.id=co.slot_id
        JOIN classes c ON c.id=co.class_id
        WHERE co.is_active=1
    """
    offering_args = []
    if teacher_id:
        offering_sql += " AND co.teacher_id=%s"
        offering_args.append(teacher_id)
    offering_sql += " ORDER BY s.subject_code"

    offerings = query_all(offering_sql, tuple(offering_args))
    classes = query_all(
        """
        SELECT c.id, d.department_code, c.class_name, c.year_label, c.section
        FROM classes c
        JOIN departments d ON d.id=c.department_id
        ORDER BY d.department_code, c.year_label, c.section
        """
    )
    students = query_all(
        """
        SELECT id, register_no, full_name
        FROM students
        ORDER BY register_no
        """
    )

    return render_template(
        "attendance_reports.html",
        role=role,
        summary=summary,
        records=records,
        course_summaries=course_summaries,
        student_summaries=student_summaries,
        session_history=session_history,
        offerings=offerings,
        classes=classes,
        students=students,
        filters={
            "offering_id": offering_id,
            "class_id": class_id,
            "student_id": student_id,
            "record_status": record_status,
            "session_status": session_status,
            "date_from": date_from,
            "date_to": date_to,
        },
    )

# -------------------------------------------------------------------
# STUDENT DASHBOARD
# -------------------------------------------------------------------

@app.route("/student")
@login_required("student")
def student_dashboard():
    student = query_one(
        """
        SELECT id, register_no, full_name
        FROM students
        WHERE user_id=%s
        """,
        (session["user_id"],),
    )

    if not student:
        flash("Student profile is not linked to this account.", "error")
        return redirect(url_for("logout"))

    rows = query_all(
        """
        SELECT
            co.id AS offering_id,
            s.subject_code,
            s.subject_name,
            sl.slot_name,
            COUNT(DISTINCT CASE
                WHEN ats.status='submitted' THEN ats.id
            END) AS conducted,
            SUM(CASE
                WHEN ats.status='submitted'
                AND ar.status IN ('present', 'present_permission')
                THEN 1 ELSE 0
            END) AS attended,
            SUM(CASE
                WHEN ats.status='submitted'
                AND ar.status='absent'
                THEN 1 ELSE 0
            END) AS absent,
            SUM(CASE
                WHEN ats.status='submitted'
                AND ar.status='present_permission'
                THEN 1 ELSE 0
            END) AS permission_count
        FROM enrollments e
        JOIN course_offerings co ON co.id=e.offering_id
        JOIN subjects s ON s.id=co.subject_id
        JOIN slots sl ON sl.id=co.slot_id
        LEFT JOIN attendance_sessions ats
            ON ats.offering_id=co.id
        LEFT JOIN attendance_records ar
            ON ar.session_id=ats.id
            AND ar.student_id=e.student_id
        WHERE e.student_id=%s
        GROUP BY
            co.id, s.subject_code, s.subject_name, sl.slot_name
        ORDER BY s.subject_name
        """,
        (student["id"],),
    )

    for row in rows:
        conducted = int(row["conducted"] or 0)
        attended = int(row["attended"] or 0)
        row["percentage"] = round(
            (attended / conducted * 100) if conducted else 0,
            2,
        )

    return render_template(
        "student_dashboard.html",
        student=student,
        courses=rows,
    )


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
