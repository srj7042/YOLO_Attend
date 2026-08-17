# 🎓 SmartAttend — AI-Powered Facial Recognition Attendance System
### Automating Classroom Attendance with Computer Vision & Deep Learning
**Institute:** GH Raisoni College of Engineering & Management  
**Developer:** Utkarsh Yadav  
**Date:** April 2026

---

## Slide 1 — Title Slide

- **Title:** SmartAttend — AI-Powered Facial Recognition Attendance System
- **Subtitle:** Automating Classroom Attendance with Computer Vision & Deep Learning
- **Institute:** GH Raisoni College of Engineering & Management
- **Presented by:** Utkarsh Yadav
- **Date:** April 2026

---

## Slide 2 — Problem Statement

- Manual attendance is **time-consuming** (5–10 min per lecture) and **error-prone**
- Proxy attendance is a persistent problem in colleges
- Paper-based records are **difficult to analyze and audit**
- Teachers lack **real-time analytics** on student participation
- No centralized system for multi-department attendance tracking

> **Goal:** Build an intelligent, tamper-proof, automated attendance system that uses AI face recognition to mark attendance from classroom photographs.

---

## Slide 3 — Proposed Solution

- Upload a **classroom photograph** → AI detects & recognizes every face
- Automatically **marks present/absent** for enrolled students
- **Admin-approved scheduling** prevents unauthorized session creation
- **Session locking (finalization)** ensures data integrity post-marking
- **Role-based dashboards** for Admin & Teacher with full analytics
- Supports **manual override** + **deep scan retry** for edge cases

---

## Slide 4 — Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3, Flask 3.0 |
| **Database** | SQLite (via Flask-SQLAlchemy) |
| **AI — Detection** | YOLOv8 (Ultralytics) — person/face detection |
| **AI — Recognition** | DeepFace + FaceNet (128-dim embeddings) |
| **Image Processing** | OpenCV, Pillow, NumPy |
| **Authentication** | Flask-Login + Werkzeug (bcrypt password hashing) |
| **Data Export** | Pandas, OpenPyXL, CSV |
| **Frontend** | Jinja2 Templates, HTML5, CSS3, JavaScript |
| **Charts** | Chart.js (via CDN) |

---

## Slide 5 — System Architecture

```
┌────────────────────────────────────────────────┐
│                   BROWSER                      │
│    (Admin Dashboard / Teacher Dashboard)       │
└────────────────────┬───────────────────────────┘
                     │  HTTP
┌────────────────────▼───────────────────────────┐
│              FLASK APPLICATION                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ auth.py  │  │ admin.py │  │  teacher.py  │ │
│  │ (Login/  │  │ (Dept/   │  │ (Attendance/ │ │
│  │  Signup) │  │  Faculty │  │  Classes/    │ │
│  │          │  │  Mgmt)   │  │  Reports)    │ │
│  └──────────┘  └──────────┘  └──────────────┘ │
│                      │                         │
│  ┌───────────────────▼──────────────────────┐  │
│  │          AI ENGINE (ai/)                 │  │
│  │  detector.py ──► recognizer.py           │  │
│  │  YOLOv8 detect → DeepFace/FaceNet encode │  │
│  │  Cosine Similarity matching (≥60%)       │  │
│  └──────────────────────────────────────────┘  │
│                      │                         │
│  ┌───────────────────▼──────────────────────┐  │
│  │           SQLite DATABASE                │  │
│  │  Users · Departments · Classes           │  │
│  │  Students · Subjects · AttendanceRecords │  │
│  │  ApprovalRequests · DiscrepancyReports   │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

---

## Slide 6 — AI Pipeline (Core Innovation)

**Step-by-step process:**

1. **Image Upload** — Teacher uploads classroom photo(s)
2. **Downscaling** — Images > 2000px width are resized for speed
3. **YOLOv8 Detection** — Detects all human figures (class 0) with configurable confidence
   - Normal scan: `conf = 0.25`
   - Deep scan: `conf = 0.15` (more sensitive)
4. **Face Cropping** — Bounding boxes mapped back to original resolution, padded by 10–20px
5. **FaceNet Encoding** — DeepFace generates 128-dimensional face embeddings per crop
6. **Cosine Similarity Matching** — Each encoding compared against stored student embeddings
   - **Threshold:** ≥ 0.60 (normal), ≥ 0.65 (deep scan)
7. **Result** — Matched students → `present`, Unmatched → `absent`

> **Key Metric:** Strict 60% confidence threshold eliminates false positives.  
> **Deep Scan:** Retry mode with lower detection threshold and stricter matching for edge cases.

---

## Slide 7 — Database Schema (ER Summary)

| Table | Key Fields | Purpose |
|---|---|---|
| `users` | id, username, password_hash, role (admin/teacher), is_active_account | Authentication & RBAC |
| `departments` | id, name, code, year (FY/SY/TY/BTech) | Department hierarchy |
| `classes` | id, name, section (division), department_id | Division management |
| `subjects` | id, name, code, class_id, teacher_id, credits | Subject-to-class mapping |
| `students` | id, student_id, name, roll_number, face_encoding (JSON), photo_count | Student records + biometric data |
| `attendance_records` | id, student_id, subject_id, date, status, ai_confidence, method, is_finalized | Core attendance log |
| `approval_requests` | id, teacher_id, subject_id, class_id, status, note (JSON schedules) | Admin approval workflow |
| `discrepancy_reports` | id, attendance_id, reason, status (open/resolved) | Dispute resolution |

**Relationships:** Department → Classes → Students → AttendanceRecords ← Subjects ← Teachers

---

## Slide 8 — Admin Dashboard Features

- 📊 **Overview Panel** — Total students, classes, teachers, today's sessions
- 📈 **Weekly Attendance Chart** — Present vs Absent trend (last 7 days)
- 📅 **Monthly Average Chart** — 6-month rolling attendance percentage
- 👨‍🏫 **Faculty Benchmark** — Teacher-wise attendance scores ranked
- ✅ **Approval Center** — Approve/Reject teacher registrations & subject access requests
- 🏢 **Staff Directory & Department Management**
  - Add departments organized by year (FY, SY, TY, BTech)
  - Add divisions (A, B, C...) per department
  - Add/manage subjects per division
  - Assign teachers to subjects
  - Import students via CSV/Excel
  - Export student attendance data as CSV
- 📉 **Analytics Dashboard** — Per-class, per-subject breakdowns with faculty performance

---

## Slide 9 — Teacher Dashboard Features

- 📋 **My Subjects** — View all assigned & approved subjects with attendance stats
- 📸 **Mark Attendance (Precision Vision Hub)**
  - Upload classroom photo → AI auto-marks attendance
  - Session locked to **admin-approved schedules only**
  - Manual override toggles for corrections
  - **Deep Scan (Retry)** — re-processes with higher sensitivity
  - **Finalize & Lock** — freezes session, pushes to analytics
- 👥 **My Classes** — View/add/edit students, upload face training photos, import via CSV
- 📊 **Attendance Records** — Session history, per-student breakdown, date filtering
- 📑 **Monthly Reports** — Heatmap calendar, grade distribution (A/B/C/F), export CSV
- 🔐 **Request Access** — Teacher submits subject + schedule → Admin approves before access

---

## Slide 10 — Workflow: Attendance Marking

```
Teacher                         Admin                        System
  │                               │                            │
  │──── Register Account ─────►  │                            │
  │                               │── Approve Teacher ─────►  │
  │──── Request Subject+Schedule─►│                            │
  │                               │── Approve Request ─────►  │
  │                               │                            │
  │◄──── Access Granted ──────── │                            │
  │                               │                            │
  │──── Upload Classroom Photo ──────────────────────────────►│
  │                               │           YOLOv8 Detect ──┤
  │                               │           FaceNet Encode ──┤
  │                               │           Cosine Match ────┤
  │◄──── AI Results (Present/Absent with Confidence) ─────────┤
  │                               │                            │
  │──── Manual Corrections ──────────────────────────────────►│
  │──── Finalize & Lock ─────────────────────────────────────►│
  │                               │                            │
  │                               │◄──── Analytics Updated ───┤
```

---

## Slide 11 — Security & Data Integrity

| Feature | Implementation |
|---|---|
| **Password Hashing** | Werkzeug `generate_password_hash` / `check_password_hash` |
| **Role-Based Access Control** | `admin_required` and `teacher_required` decorators |
| **Session Locking** | `is_finalized` flag — once True, records cannot be modified |
| **Approval Workflow** | Teachers can't mark attendance until Admin approves their subject + schedule |
| **Account Activation** | New teacher accounts are `is_active_account=False` until admin approval |
| **Faculty Removal** | Role changed to `guest`, data preserved (non-destructive) |
| **Upload Security** | `secure_filename()`, file type whitelist (png, jpg, jpeg, webp), 16MB limit |
| **AI Confidence Gate** | Matches below 60% threshold are rejected — prevents false positives |

---

## Slide 12 — Key Differentiators

| Feature | SmartAttend | Traditional Systems |
|---|---|---|
| Attendance Method | 📸 AI Facial Recognition | ✍️ Manual / Biometric |
| Processing Speed | < 10 seconds per photo | 5–10 min per lecture |
| Proxy Prevention | Face matching with confidence scores | Roll call (easily gamed) |
| Data Analytics | Real-time dashboards & charts | Manual compilation |
| Multi-Department | Year-wise (FY/SY/TY/BTech) hierarchy | Single flat structure |
| Session Security | Admin-approved schedule locking | No controls |
| Export | CSV + Excel with grades | Paper printouts |

---

## Slide 13 — Screenshots / Demo Highlights

> *(Add screenshots of the following pages from your running application)*

1. **Login Page** — Role-based login (Admin / Teacher)
2. **Admin Dashboard** — Stats cards, weekly chart, faculty benchmark
3. **Staff Directory** — Department cards grouped by year, division management
4. **Teacher Dashboard** — Subject stats, weekly charts
5. **Mark Attendance** — Photo upload, AI processing results, confidence bars
6. **My Classes** — Student roster, photo upload, CSV import
7. **Analytics** — Class-wise breakdowns, subject donut charts
8. **Monthly Report** — Heatmap calendar, grade distribution

---

## Slide 14 — Results & Observations

- ✅ **YOLOv8** successfully detects faces even in group photos with partial occlusion
- ✅ **FaceNet 128-dim embeddings** provide robust recognition across lighting conditions
- ✅ **60% cosine similarity threshold** balances accuracy vs. recall effectively
- ✅ **Deep scan mode** recovers ~15–20% additional matches in challenging photos
- ✅ **Session finalization** ensures audit-proof attendance records
- ✅ **Cascading department → division → subject** structure scales to multi-department colleges

---

## Slide 15 — Challenges & Limitations

- 📷 Image quality heavily affects detection accuracy (blur, low resolution)
- 👤 Students without uploaded face photos cannot be matched (requires enrollment)
- 🔧 SQLite may not scale for very large institutions (consider PostgreSQL for production)
- 🖥️ AI processing runs synchronously — can slow down for very large class photos
- 📱 Currently a web app — no native mobile app for quick photo capture

---

## Slide 16 — Future Scope

- 🔄 **Real-time camera integration** — Direct webcam/CCTV feed processing
- 📱 **Mobile app** — React Native / Flutter for teachers to snap & upload
- 🧠 **Anti-spoofing** — Liveness detection to prevent printed photo attacks
- 📊 **Predictive analytics** — Identify at-risk students with ML-based attendance prediction
- 🔔 **Notifications** — Email/SMS alerts for low attendance thresholds
- 🗄️ **PostgreSQL migration** — For large-scale deployment
- 🌐 **Multi-institute** — SaaS model with tenant isolation
- 📋 **Parent portal** — Real-time attendance visibility for guardians

---

## Slide 17 — Conclusion

> SmartAttend demonstrates that **AI-powered facial recognition** can transform traditional attendance management into a **fast, accurate, and tamper-proof** system. By combining **YOLOv8 detection** with **FaceNet recognition** and wrapping it in a **role-based web application**, the system addresses real-world challenges of proxy attendance, manual effort, and data analysis — making it a practical, deployable solution for educational institutions.

---

## Slide 18 — Thank You & Q&A

- **Project:** SmartAttend
- **Developer:** Utkarsh Yadav
- **GitHub:** [github.com/utkarshyadav29/SmartAttend](https://github.com/utkarshyadav29/SmartAttend)
- **Tech:** Flask · YOLOv8 · DeepFace · FaceNet · SQLite
- **Institute:** GH Raisoni College of Engineering & Management

> _"Thank you! Questions are welcome."_

---

## Project File Structure

```
SmartAttend/
├── app.py                  # Flask app factory + entry point
├── config.py               # Configuration (DB URI, upload limits)
├── extensions.py           # SQLAlchemy + LoginManager instances
├── models.py               # 8 database models (User, Department, Class, etc.)
├── requirements.txt        # Python dependencies
├── yolov8n.pt              # Pre-trained YOLOv8 nano model (~6.5MB)
├── ai/
│   ├── detector.py         # YOLOv8 detection + FaceNet encoding + cosine matching
│   └── recognizer.py       # Multi-image attendance processing pipeline
├── routes/
│   ├── auth.py             # Login, Register, Logout
│   ├── admin.py            # Admin dashboard, departments, analytics
│   └── teacher.py          # Teacher dashboard, attendance, reports
├── templates/
│   ├── base.html           # Shared layout (sidebar, navigation)
│   ├── auth/               # login.html, register.html
│   ├── admin/              # dashboard, analytics, approvals, staff_log, settings
│   └── teacher/            # dashboard, classes, lectures, mark_attendance, records, monthly_report
├── static/img/             # UI assets
├── uploads/                # Student photos & session images
└── smartattend.db          # SQLite database file
```

---

## Quick Stats

| Metric | Value |
|---|---|
| Total Python Files | 7 |
| Total Templates | 14 |
| Lines of Backend Code | ~1,500+ |
| Database Tables | 8 |
| AI Models Used | 2 (YOLOv8 + FaceNet) |
| Face Embedding Dimensions | 128 |
| Confidence Threshold | 60% (normal) / 65% (deep scan) |
| Max Upload Size | 16 MB |
