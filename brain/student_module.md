# Student Module Specification

## Overview

The Student Module provides a secure, role-isolated portal for enrolled students in the SmartAttend system. Students can authenticate using their **Roll Number** or **Student ID** and view their personalized attendance statistics, subject breakdown, and attendance history without access to administrative or teaching tools.

---

## 1. Authentication & Security

- **Login Credentials**: Roll Number or Student ID + Password.
- **Default Password**: Set to `roll_number` (or `student_id` if roll number is missing) when a student is created or imported via CSV/Excel by a teacher.
- **Flask-Login Role**: `current_user.role == 'student'`.
- **Role Isolation Guard (`@student_required`)**:
  ```python
  def student_required(f):
      @wraps(f)
      def decorated(*args, **kwargs):
          if not current_user.is_authenticated or current_user.role != 'student':
              flash('Student access required.', 'error')
              return redirect(url_for('auth.login'))
          return f(*args, **kwargs)
      return decorated
  ```
- **Data Protection**:
  - Students cannot access `/admin/*` or `/teacher/*` routes.
  - Students can only query `AttendanceRecord` where `student_id == current_user.student_profile.id`.
  - Students cannot edit attendance, register face photos, manage classes, or download full-institution reports.

---

## 2. Student Portal Endpoints (`/student`)

| Endpoint | Method | Purpose | Protection |
| :--- | :--- | :--- | :--- |
| `/student/dashboard` | `GET` | Main personalized student dashboard | `@student_required` |
| `/student/photo` | `GET` | Serves logged-in student's profile photo | `@student_required` |
| `/student/change-password` | `POST` | Updates logged-in student password | `@student_required` |

---

## 3. Data Models & Database Integration

- **User Model Update**: Added `student_id = db.Column(db.Integer, db.ForeignKey('students.id'))` and `student_profile` relationship back to `Student`.
- **Automatic User Creation**:
  - `routes/teacher.py:add_student`: Auto-creates a `User` record (`role='student'`, `username=student_id`, `password=roll_number`) on manual student creation.
  - `routes/teacher.py:import_students_csv`: Auto-creates `User` accounts for all new students imported via CSV/Excel.

---

## 4. Frontend & Visualizations

- **Profile Banner**: Avatar, Full Name, Student ID, Roll Number, Department, Class/Year/Division, Email.
- **KPI Summary Cards**: Overall Attendance %, Lectures Attended, Lectures Missed, Total Conducted.
- **Subject-Wise Breakdown**: Progress bars, Present/Conducted count, and Shortage Warning badges (<75%).
- **Attendance History Log**: Detailed log with Date, Time Slot, Subject Name & Code, Faculty Name, AI YOLO/Manual status badges.
- **Chart.js Integration**:
  - Bar Chart: Subject-wise attendance percentage comparison.
  - Line Chart: Weekly attendance trend (Present vs. Absent).
- **Change Password Modal**: Form with current password validation and minimum 6-character length constraint.
