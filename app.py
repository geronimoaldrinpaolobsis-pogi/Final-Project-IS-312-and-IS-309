from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from functools import wraps
from typing import Optional

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

# Railway-friendly writable path for SQLite
DB_PATH = os.environ.get("DATABASE_PATH", "/tmp/database.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-in-production")
app.config["DATABASE"] = DB_PATH


# ------------------------------
# Database helpers
# ------------------------------
def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception: Optional[BaseException]) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student', 'staff', 'admin')),
            email TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            purpose TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Approved', 'Rejected')),
            staff_note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS student_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL UNIQUE,
            student_number TEXT NOT NULL,
            course TEXT NOT NULL,
            year_level TEXT NOT NULL,
            contact_number TEXT DEFAULT '',
            address TEXT DEFAULT '',
            guardian_name TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            log_time TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )
    db.commit()
    seed_data()


def seed_data() -> None:
    db = get_db()
    existing = db.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    if existing > 0:
        return

    now = timestamp()
    users = [
        ("Alice Student", "student1", generate_password_hash("student123"), "student", "student1@example.com", now),
        ("Bob Staff", "staff1", generate_password_hash("staff123"), "staff", "staff1@example.com", now),
        ("Cara Admin", "admin1", generate_password_hash("admin123"), "admin", "admin1@example.com", now),
    ]
    db.executemany(
        "INSERT INTO users (full_name, username, password_hash, role, email, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        users,
    )

    student_id = db.execute("SELECT id FROM users WHERE username = 'student1'").fetchone()["id"]
    db.execute(
        """
        INSERT INTO student_records
        (student_id, student_number, course, year_level, contact_number, address, guardian_name, notes, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            student_id,
            "2026-0001",
            "BS Information Systems",
            "3rd Year",
            "09123456789",
            "Sample City",
            "Maria Student",
            "Eligible for advising and appointment services.",
            now,
        ),
    )

    db.executemany(
        "INSERT INTO announcements (title, content, created_at) VALUES (?, ?, ?)",
        [
            ("Welcome", "Welcome to the Smart Student Appointment and Record Management System.", now),
            ("Privacy Reminder", "Only authorized users should access records. Handle personal data responsibly.", now),
        ],
    )
    db.commit()


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_action(user_id: Optional[int], action: str) -> None:
    try:
        db = get_db()
        db.execute(
            "INSERT INTO activity_logs (user_id, action, log_time) VALUES (?, ?, ?)",
            (user_id, action, timestamp()),
        )
        db.commit()
    except sqlite3.Error:
        pass


# ------------------------------
# Security helpers
# ------------------------------
def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if session.get("user_id") is None:
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You are not authorized to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def current_user() -> Optional[sqlite3.Row]:
    user_id = session.get("user_id")
    if not user_id:
        return None
    try:
        return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.Error:
        return None


@app.before_request
def before_request() -> None:
    g.user = current_user()


# ------------------------------
# Routes
# ------------------------------
@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "danger")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["role"] = user["role"]
        session["full_name"] = user["full_name"]
        log_action(user["id"], f"Logged in as {user['role']}")
        flash("Login successful.", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    user_id = session.get("user_id")
    log_action(user_id, "Logged out")
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    announcements = db.execute("SELECT * FROM announcements ORDER BY id DESC").fetchall()

    if session["role"] == "student":
        appointments = db.execute(
            "SELECT * FROM appointments WHERE student_id = ? ORDER BY appointment_date, appointment_time",
            (session["user_id"],),
        ).fetchall()
        record = db.execute(
            "SELECT * FROM student_records WHERE student_id = ?",
            (session["user_id"],),
        ).fetchone()
        return render_template(
            "student_dashboard.html",
            announcements=announcements,
            appointments=appointments,
            record=record,
        )

    if session["role"] == "staff":
        appointments = db.execute(
            """
            SELECT appointments.*, users.full_name
            FROM appointments
            JOIN users ON appointments.student_id = users.id
            ORDER BY appointments.created_at DESC
            """
        ).fetchall()
        return render_template("staff_dashboard.html", announcements=announcements, appointments=appointments)

    user_count = db.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    appt_count = db.execute("SELECT COUNT(*) AS count FROM appointments").fetchone()["count"]
    logs = db.execute(
        """
        SELECT activity_logs.*, users.full_name
        FROM activity_logs
        LEFT JOIN users ON activity_logs.user_id = users.id
        ORDER BY activity_logs.id DESC
        LIMIT 15
        """
    ).fetchall()
    return render_template(
        "admin_dashboard.html",
        announcements=announcements,
        user_count=user_count,
        appt_count=appt_count,
        logs=logs,
    )


@app.route("/appointments", methods=["GET", "POST"])
@login_required
@role_required("student")
def appointments():
    db = get_db()
    if request.method == "POST":
        appointment_date = request.form.get("appointment_date", "").strip()
        appointment_time = request.form.get("appointment_time", "").strip()
        purpose = request.form.get("purpose", "").strip()

        if not appointment_date or not appointment_time or not purpose:
            flash("All fields are required.", "danger")
        elif len(purpose) < 10:
            flash("Purpose must be at least 10 characters long.", "danger")
        else:
            db.execute(
                """
                INSERT INTO appointments (student_id, appointment_date, appointment_time, purpose, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session["user_id"], appointment_date, appointment_time, purpose, timestamp()),
            )
            db.commit()
            log_action(session["user_id"], "Created an appointment request")
            flash("Appointment request submitted.", "success")
            return redirect(url_for("appointments"))

    appointments_data = db.execute(
        "SELECT * FROM appointments WHERE student_id = ? ORDER BY created_at DESC",
        (session["user_id"],),
    ).fetchall()
    return render_template("appointments.html", appointments=appointments_data)


@app.route("/manage-appointments", methods=["GET", "POST"])
@login_required
@role_required("staff", "admin")
def manage_appointments():
    db = get_db()
    if request.method == "POST":
        appointment_id = request.form.get("appointment_id", "").strip()
        status = request.form.get("status", "").strip()
        staff_note = request.form.get("staff_note", "").strip()
        if status not in {"Pending", "Approved", "Rejected"}:
            flash("Invalid appointment status.", "danger")
        else:
            db.execute(
                "UPDATE appointments SET status = ?, staff_note = ? WHERE id = ?",
                (status, staff_note, appointment_id),
            )
            db.commit()
            log_action(session["user_id"], f"Updated appointment #{appointment_id} to {status}")
            flash("Appointment updated.", "success")
            return redirect(url_for("manage_appointments"))

    appointments_data = db.execute(
        """
        SELECT appointments.*, users.full_name
        FROM appointments
        JOIN users ON appointments.student_id = users.id
        ORDER BY appointments.created_at DESC
        """
    ).fetchall()
    return render_template("manage_appointments.html", appointments=appointments_data)


@app.route("/records", methods=["GET", "POST"])
@login_required
@role_required("staff", "admin")
def records():
    db = get_db()
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        student_number = request.form.get("student_number", "").strip()
        course = request.form.get("course", "").strip()
        year_level = request.form.get("year_level", "").strip()
        contact_number = request.form.get("contact_number", "").strip()
        address = request.form.get("address", "").strip()
        guardian_name = request.form.get("guardian_name", "").strip()
        notes = request.form.get("notes", "").strip()

        if not student_id or not student_number or not course or not year_level:
            flash("Student, student number, course, and year level are required.", "danger")
        else:
            existing = db.execute("SELECT id FROM student_records WHERE student_id = ?", (student_id,)).fetchone()
            if existing:
                db.execute(
                    """
                    UPDATE student_records
                    SET student_number = ?, course = ?, year_level = ?, contact_number = ?,
                        address = ?, guardian_name = ?, notes = ?, updated_at = ?
                    WHERE student_id = ?
                    """,
                    (student_number, course, year_level, contact_number, address, guardian_name, notes, timestamp(), student_id),
                )
                message = "Record updated."
            else:
                db.execute(
                    """
                    INSERT INTO student_records
                    (student_id, student_number, course, year_level, contact_number, address, guardian_name, notes, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (student_id, student_number, course, year_level, contact_number, address, guardian_name, notes, timestamp()),
                )
                message = "Record created."
            db.commit()
            log_action(session["user_id"], f"Managed record for user #{student_id}")
            flash(message, "success")
            return redirect(url_for("records"))

    students = db.execute("SELECT id, full_name, username FROM users WHERE role = 'student' ORDER BY full_name ASC").fetchall()
    record_rows = db.execute(
        """
        SELECT student_records.*, users.full_name, users.username
        FROM student_records
        JOIN users ON student_records.student_id = users.id
        ORDER BY users.full_name ASC
        """
    ).fetchall()
    return render_template("records.html", students=students, records=record_rows)


@app.route("/users", methods=["GET", "POST"])
@login_required
@role_required("admin")
def users():
    db = get_db()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "").strip()
        email = request.form.get("email", "").strip()

        if not full_name or not username or not password or role not in {"student", "staff", "admin"}:
            flash("Please complete all required fields correctly.", "danger")
        else:
            try:
                db.execute(
                    """
                    INSERT INTO users (full_name, username, password_hash, role, email, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (full_name, username, generate_password_hash(password), role, email, timestamp()),
                )
                db.commit()
                log_action(session["user_id"], f"Created user {username} with role {role}")
                flash("User created successfully.", "success")
                return redirect(url_for("users"))
            except sqlite3.IntegrityError:
                flash("Username already exists.", "danger")

    all_users = db.execute("SELECT id, full_name, username, role, email, created_at FROM users ORDER BY id ASC").fetchall()
    return render_template("users.html", users=all_users)


@app.route("/logs")
@login_required
@role_required("admin")
def logs():
    log_rows = get_db().execute(
        """
        SELECT activity_logs.*, users.full_name, users.username
        FROM activity_logs
        LEFT JOIN users ON activity_logs.user_id = users.id
        ORDER BY activity_logs.id DESC
        """
    ).fetchall()
    return render_template("logs.html", logs=log_rows)


@app.route("/ethics")
@login_required
def ethics():
    return render_template("ethics.html")


@app.route("/health")
def health():
    return {"status": "ok"}


@app.errorhandler(Exception)
def handle_error(error):
    return f"Application error: {error}", 500


with app.app_context():
    init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
