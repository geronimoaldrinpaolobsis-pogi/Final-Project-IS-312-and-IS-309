# Smart Student Appointment and Record Management System

A simple Flask + SQLite web application for an IS 312 final activity.

## Features
- User login and role-based access
- Student dashboard
- Appointment booking and approval workflow
- Student record management
- Admin user management and activity logs
- Security, privacy, and ethics page

## Tech Stack
- HTML
- CSS
- Python (Flask)
- SQLite database

## Project Structure
- `app.py` - main Flask application
- `templates/` - HTML templates
- `static/style.css` - CSS styling
- `database.db` - SQLite database, created automatically on first run

## How to Run

### 1. Open a terminal in the project folder
```bash
cd is312_system
```

### 2. Create a virtual environment
**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Start the application
```bash
python app.py
```

### 5. Open the browser
Go to:
```text
http://127.0.0.1:5000
```

## Demo Accounts
- Student: `student1` / `student123`
- Staff: `staff1` / `staff123`
- Admin: `admin1` / `admin123`

## Notes
- Change the Flask `SECRET_KEY` for production use.
- This is a classroom prototype, not a production deployment.
- Passwords are hashed before being stored.
- The database is automatically seeded the first time the app runs.

## Suggested Group Module Assignments
1. Login and Authentication Module
2. Student Dashboard Module
3. Appointment Booking Module
4. Record Management Module
5. Admin and Monitoring Module
