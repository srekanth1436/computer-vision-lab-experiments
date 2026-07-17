from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor
from werkzeug.security import generate_password_hash

import config


def connect(database=None):
    return pymysql.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


def get_or_create(cursor, select_sql, select_args, insert_sql, insert_args):
    cursor.execute(select_sql, select_args)
    row = cursor.fetchone()

    if row:
        return row["id"]

    cursor.execute(insert_sql, insert_args)
    return cursor.lastrowid


def column_exists(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=%s
          AND TABLE_NAME=%s
          AND COLUMN_NAME=%s
        """,
        (config.MYSQL_DATABASE, table_name, column_name),
    )
    return cursor.fetchone()["total"] > 0


def migrate_phase5(cursor):
    """
    Upgrade an existing Phase 4 database without deleting any data.
    """

    if not column_exists(cursor, "course_offerings", "room_name"):
        cursor.execute(
            """
            ALTER TABLE course_offerings
            ADD COLUMN room_name VARCHAR(80) NULL
            AFTER semester
            """
        )

    if not column_exists(cursor, "timetable_entries", "slot_schedule_id"):
        cursor.execute(
            """
            ALTER TABLE timetable_entries
            ADD COLUMN slot_schedule_id INT NULL
            AFTER offering_id
            """
        )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS slot_schedules (
            id INT AUTO_INCREMENT PRIMARY KEY,
            slot_id INT NOT NULL,
            day_of_week TINYINT NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_slot_schedule (
                slot_id, day_of_week, start_time, end_time
            ),
            FOREIGN KEY (slot_id) REFERENCES slots(id) ON DELETE CASCADE
        )
        """
    )

    # Keep the room already used by each course assignment.
    cursor.execute(
        """
        UPDATE course_offerings co
        JOIN (
            SELECT offering_id, MAX(room_name) AS saved_room
            FROM timetable_entries
            WHERE room_name IS NOT NULL AND room_name <> ''
            GROUP BY offering_id
        ) rooms ON rooms.offering_id=co.id
        SET co.room_name=COALESCE(co.room_name, rooms.saved_room)
        """
    )

    # Convert old manually entered timetable rows into reusable slot rules.
    cursor.execute(
        """
        INSERT IGNORE INTO slot_schedules
        (slot_id, day_of_week, start_time, end_time)
        SELECT DISTINCT
            co.slot_id,
            tt.day_of_week,
            tt.start_time,
            tt.end_time
        FROM timetable_entries tt
        JOIN course_offerings co ON co.id=tt.offering_id
        """
    )

    # Link old timetable entries with their matching master slot rule.
    cursor.execute(
        """
        UPDATE timetable_entries tt
        JOIN course_offerings co ON co.id=tt.offering_id
        JOIN slot_schedules ss
          ON ss.slot_id=co.slot_id
         AND ss.day_of_week=tt.day_of_week
         AND ss.start_time=tt.start_time
         AND ss.end_time=tt.end_time
        SET tt.slot_schedule_id=ss.id
        WHERE tt.slot_schedule_id IS NULL
        """
    )


def sync_all_slot_schedules(cursor):
    """
    Apply every master slot rule to every active course assigned to that slot.
    """

    cursor.execute(
        """
        SELECT
            ss.id AS schedule_id,
            ss.slot_id,
            ss.day_of_week,
            ss.start_time,
            ss.end_time
        FROM slot_schedules ss
        ORDER BY ss.slot_id, ss.day_of_week, ss.start_time
        """
    )
    schedules = cursor.fetchall()

    for schedule in schedules:
        cursor.execute(
            """
            SELECT id, room_name
            FROM course_offerings
            WHERE slot_id=%s AND is_active=1
            """,
            (schedule["slot_id"],),
        )
        offerings = cursor.fetchall()

        for offering in offerings:
            cursor.execute(
                """
                SELECT id, slot_schedule_id
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
                        schedule["schedule_id"],
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
                        schedule["schedule_id"],
                        schedule["day_of_week"],
                        schedule["start_time"],
                        schedule["end_time"],
                        offering["room_name"],
                    ),
                )


def main():
    server = connect()

    try:
        with server.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.MYSQL_DATABASE}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        server.commit()
    finally:
        server.close()

    connection = connect(config.MYSQL_DATABASE)

    try:
        with connection.cursor() as cursor:
            schema = Path("database.sql").read_text(encoding="utf-8")

            for statement in schema.split(";"):
                statement = statement.strip()

                if statement:
                    cursor.execute(statement)

            migrate_phase5(cursor)

            for code in ("A", "B", "C", "D"):
                cursor.execute(
                    """
                    INSERT INTO slots (slot_code, slot_name)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE slot_name=VALUES(slot_name)
                    """,
                    (code, f"Slot {code}"),
                )

            department_id = get_or_create(
                cursor,
                "SELECT id FROM departments WHERE department_code=%s",
                ("CSE",),
                """
                INSERT INTO departments
                (department_code, department_name)
                VALUES (%s, %s)
                """,
                ("CSE", "Computer Science and Engineering"),
            )

            class_id = get_or_create(
                cursor,
                """
                SELECT id
                FROM classes
                WHERE department_id=%s
                  AND class_name=%s
                  AND year_label=%s
                  AND section=%s
                """,
                (department_id, "B.Tech CSE", "III Year", "A"),
                """
                INSERT INTO classes
                (department_id, class_name, year_label, section)
                VALUES (%s, %s, %s, %s)
                """,
                (department_id, "B.Tech CSE", "III Year", "A"),
            )

            get_or_create(
                cursor,
                "SELECT id FROM users WHERE username=%s",
                ("admin",),
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, 'admin')
                """,
                ("admin", generate_password_hash("admin123")),
            )

            teacher_user_id = get_or_create(
                cursor,
                "SELECT id FROM users WHERE username=%s",
                ("jeena",),
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, 'teacher')
                """,
                ("jeena", generate_password_hash("teacher123")),
            )

            teacher_id = get_or_create(
                cursor,
                "SELECT id FROM teachers WHERE employee_no=%s",
                ("T001",),
                """
                INSERT INTO teachers
                (user_id, employee_no, full_name, department_id)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    teacher_user_id,
                    "T001",
                    "Dr. R. Jeena",
                    department_id,
                ),
            )

            student_user_id = get_or_create(
                cursor,
                "SELECT id FROM users WHERE username=%s",
                ("sreekanth",),
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, 'student')
                """,
                ("sreekanth", generate_password_hash("student123")),
            )

            student_id = get_or_create(
                cursor,
                "SELECT id FROM students WHERE register_no=%s",
                ("192372037",),
                """
                INSERT INTO students
                (
                    user_id, register_no, full_name,
                    class_id, face_registered
                )
                VALUES (%s, %s, %s, %s, FALSE)
                """,
                (
                    student_user_id,
                    "192372037",
                    "V Sreekanth",
                    class_id,
                ),
            )

            subject_id = get_or_create(
                cursor,
                "SELECT id FROM subjects WHERE subject_code=%s",
                ("ITA0510",),
                """
                INSERT INTO subjects
                (subject_code, subject_name, department_id)
                VALUES (%s, %s, %s)
                """,
                ("ITA0510", "Computer Vision", department_id),
            )

            cursor.execute("SELECT id FROM slots WHERE slot_code='A'")
            slot_a_id = cursor.fetchone()["id"]

            offering_id = get_or_create(
                cursor,
                """
                SELECT id
                FROM course_offerings
                WHERE subject_id=%s
                  AND class_id=%s
                  AND slot_id=%s
                  AND teacher_id=%s
                  AND academic_year=%s
                  AND semester=%s
                """,
                (
                    subject_id,
                    class_id,
                    slot_a_id,
                    teacher_id,
                    "2026-2027",
                    "Semester 5",
                ),
                """
                INSERT INTO course_offerings
                (
                    subject_id, class_id, slot_id, teacher_id,
                    academic_year, semester, room_name
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    subject_id,
                    class_id,
                    slot_a_id,
                    teacher_id,
                    "2026-2027",
                    "Semester 5",
                    "CV Lab",
                ),
            )

            cursor.execute(
                """
                UPDATE course_offerings
                SET room_name=COALESCE(room_name, 'CV Lab')
                WHERE id=%s
                """,
                (offering_id,),
            )

            cursor.execute(
                """
                INSERT IGNORE INTO enrollments (offering_id, student_id)
                VALUES (%s, %s)
                """,
                (offering_id, student_id),
            )

            # Keep the original sample Slot A rule only for a fresh project.
            cursor.execute("SELECT COUNT(*) AS total FROM slot_schedules")
            if cursor.fetchone()["total"] == 0:
                cursor.execute(
                    """
                    INSERT IGNORE INTO slot_schedules
                    (slot_id, day_of_week, start_time, end_time)
                    VALUES (%s, 0, '13:00:00', '15:00:00')
                    """,
                    (slot_a_id,),
                )

            sync_all_slot_schedules(cursor)

        connection.commit()

        print("Database upgraded successfully for Phase 5.")
        print("Existing students, faces, attendance and reports are preserved.")
        print("Admin   : admin / admin123")
        print("Teacher : jeena / teacher123")
        print("Student : sreekanth / student123")

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
