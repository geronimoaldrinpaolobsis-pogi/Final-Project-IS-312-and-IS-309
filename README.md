# Smart Student Appointment and Record Management System

A simple Flask + SQLite web application for an IS 312 and 313 final project.

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

cd is312_system

### 2. Install dependencies
pip install -r requirements.txt


### 4. Start the application
python app.py


### 5. Open the browser
http://127.0.0.1:5000

## Demo Accounts
- Student: `student1` / `student123`
- Staff: `staff1` / `staff123`
- Admin: `admin1` / `admin123`

## Notes
- This is a classroom prototype, not a production deployment.
- Passwords are hashed before being stored.
- The database is automatically seeded the first time the app runs.

## Suggested Group Module Assignments
1. Login and Authentication Module
2. Student Dashboard Module
3. Appointment Booking Module
4. Record Management Module
5. Admin and Monitoring Module
