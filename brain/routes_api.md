# API & Route Specifications

## Summary of Blueprints

| Blueprint | Prefix | File | Purpose |
| :--- | :--- | :--- | :--- |
| `auth_bp` | `/auth` | [routes/auth.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/routes/auth.py) | Authentication, registration, logout |
| `admin_bp` | `/admin` | [routes/admin.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/routes/admin.py) | Institution management, staff approvals, analytics |
| `teacher_bp` | `/teacher` | [routes/teacher.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/routes/teacher.py) | Class rosters, photo enrollment, AI attendance |

---

## Auth Endpoints (`/auth`)

- `GET|POST /auth/login`
  - Params: `username`, `password`, `role` (`admin` | `teacher`), `remember` (`on`).
  - Action: Verifies credentials, executes `login_user()`, redirects based on role.
- `GET|POST /auth/register`
  - Params: `name`, `username`, `email`, `password`.
  - Action: Registers inactive teacher account (`is_active_account=False`).
- `GET /auth/logout`
  - Action: Executes `logout_user()`, redirects to `/auth/login`.

---

## Admin Endpoints (`/admin`)

- `GET /admin/dashboard`: Dashboard with system statistics, weekly attendance chart data, and monthly trends.
- `GET /admin/staff_log`: Staff management view, department listing, division overview, and faculty roster.
- `POST /admin/add_department`: Form params: `dept_name`, `dept_code`.
- `POST /admin/delete_department/<int:id>`: Deletes department and cascade targets.
- `POST /admin/add_class`: Form params: `dept_id`, `section`. Creates class named `"{dept.name}"` with section.
- `POST /admin/delete_class/<int:id>`: Deletes target class/division.
- `POST /admin/add_teacher`: Form params: `name`, `username`, `email`, `department`, `employee_id`, `password`.
- `POST /admin/toggle_teacher_status/<int:id>`: Toggles `is_active_account` between True/False.
- `POST /admin/delete_teacher/<int:id>`: Deletes teacher account.
- `GET /admin/approvals`: Lists pending/history subject assignment requests.
- `POST /admin/approve_request/<int:id>`: Approves request, links teacher ID to Subject.
- `POST /admin/reject_request/<int:id>`: Rejects approval request.
- `GET /admin/analytics`: Detailed system-wide analytics, department averages, low attendance alerts.
- `GET|POST /admin/settings`: Institution settings management (e.g. system name, attendance thresholds).

---

## Teacher Endpoints (`/teacher`)

- `GET /teacher/dashboard`: Assigned subjects, weekly chart data, session stats.
- `GET|POST /teacher/request-access`: Submits approval request for subject/class access.
- `GET /teacher/classes` or `/teacher/classes/<int:subject_id>`: Class roster, student attendance rates, photo count.
- `GET|POST /teacher/lectures`: Creates new department/class/subject request payload for admin approval.
- `POST /teacher/classes/<int:subject_id>/add-student`: Manual single student creation (`student_id`, `name`, `roll_number`, `email`, `address`).
- `POST /teacher/classes/edit-student/<int:student_id>`: Edits existing student profile.
- `POST /teacher/classes/<int:subject_id>/import-csv`: Batch imports students from CSV/XLSX file.
- `POST /teacher/classes/upload-photo/<int:student_id>`: Uploads training photos, triggers DeepFace encoding generation.
- `POST /teacher/classes/delete-photo/<int:student_id>/<filename>`: Deletes student training photo.
- `GET|POST /teacher/mark-attendance`:
  - `GET`: Select subject and date to view current attendance status.
  - `POST`: Upload classroom photos, runs YOLO + DeepFace matching, updates `AttendanceRecord`. Supports `retry=1` for Deep Scan.
- `POST /teacher/finalize-attendance`: Locks session (`is_finalized=True`).
- `GET /teacher/records`: Historical session logs & student summary reports.
- `POST /teacher/delete-session`: JSON body `{subject_id, date, time_slot}`. Deletes attendance records for session.
- `GET /teacher/records/export`: Downloads CSV report for subject (`?subject_id=<id>`).
- `GET /teacher/monthly-report`: Detailed monthly heatmap & student grade summary.

### API Utility Endpoints (JSON)
- `GET /teacher/student_photos/<int:student_id>`: Returns JSON `{photos: [filename, ...]}`.
- `GET /teacher/student_photo/<int:student_id>/<filename>`: Serves raw photo file.
- `GET /teacher/api/subject_divisions/<int:subject_id>`: Returns divisions associated with subject name.
- `GET /teacher/api/approved_schedules/<int:subject_id>`: Returns JSON array of approved lecture dates/times.
- `POST /teacher/api/mark-attendance-manual`: JSON body `{student_id, subject_id, date, status}`. Creates/updates manual override record.
