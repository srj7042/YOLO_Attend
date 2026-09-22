# 🎓 SmartAttend (YOLO_Attend)
### AI-Powered Facial Recognition Attendance & Student Training System

![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)
![YOLOv8](https://img.shields.io/badge/YOLO-v8-orange.svg)
![DeepFace](https://img.shields.io/badge/DeepFace-FaceNet-red.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)

**SmartAttend** is a full-stack, enterprise-grade AI attendance management platform designed for educational institutions. It automates classroom attendance by detecting and identifying faces in group classroom photographs using **YOLOv8** computer vision and **DeepFace / FaceNet** biometric embeddings.

---

## 🌟 Key Features

### 1. 🤖 AI Attendance Marking (YOLOv8 + DeepFace)
- **High-Resolution Crowd Detection**: Uses YOLOv8 Medium (`yolov8m.pt`) with multi-scale inference (`imgsz=1280`) to accurately localize students even in dense, distant lecture hall rows.
- **Deep Biometric Embeddings**: Generates 128-dimensional facial vectors via FaceNet with OpenCV face alignment.
- **Cosine Similarity Matching**: Matches live classroom captures against stored student biometrics (threshold $\ge 0.60$; Deep Scan $\ge 0.65$).
- **Deep Scan Retry**: Enhanced secondary scan pass with lower confidence thresholds and stricter IoU filters for difficult lighting or partial face occlusions.

### 2. 🧠 Student AI Training Center (Admin Panel)
- **Dynamic Student Dataset Grid**: View all registered students with real-time biometric training statuses (`Trained`, `Training`, `Not Trained`).
- **Per-Student Photo Management**: Upload multiple high-resolution reference photos per student with drag-and-drop simplicity and isolated folder storage (`uploads/training_images/student_<id>/`).
- **Individual Training**: Train and update biometric encodings for a single student on-demand.
- **Bulk Training ("Train All Students")**: One-click batch training across all students in the database with uploaded photos.
- **Dynamic Multi-Filters**: Instant client-side filtering by Department, Class/Division, Training Status, and full-text Search (Name, Roll No, Reg No).

### 3. 📋 Student Registration & Verification Workflow
- **Application Queue**: Multi-tab interface separating `Pending Applications`, `Verified Students`, `Add Student`, and `CSV Upload`.
- **Automatic Identity Generation**: Auto-generates official branch registration numbers (`ACSE`, `ACOE`, `AIFT`) and sequential roll numbers upon verification.
- **Bulk CSV Import & Preview**: Validates email/phone uniqueness, schema integrity, and branch assignments before importing.

### 4. 👥 Role-Based Access Control (RBAC)
- **Master Admin**: Full institutional oversight, Department & Division management, Staff approvals, Student Training Center, Permissions matrix, and Audit Logging.
- **Director / Dean**: High-level cross-department attendance statistics, faculty performance indicators, and institutional trends.
- **HOD (Head of Department)**: Department-level class performance analytics and subject oversight.
- **Teacher**: Lecture scheduling, classroom image upload & AI attendance processing, manual overrides, discrepancy tracking, and CSV/Excel report exports.
- **Student**: Personal attendance ledger, monthly participation charts, and subject-wise breakdown.

### 5. 📊 Analytics & Reporting
- Real-time weekly participation trends and faculty benchmark charts powered by **Chart.js**.
- One-click export to **CSV** and **Excel** for division-wise and subject-wise attendance ledgers.
- Tamper-proof session finalization preventing post-lecture alteration.

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────┐
│                   WEB CLIENT BROWSER                   │
│   (Admin / Teacher / HOD / Director / Student Portals) │
└───────────────────────────┬────────────────────────────┘
                            │  HTTP / REST APIs
┌───────────────────────────▼────────────────────────────┐
│                    FLASK APPLICATION                   │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ │
│  │   routes/     │ │   routes/     │ │   routes/     │ │
│  │   auth.py     │ │   admin.py    │ │   teacher.py  │ │
│  └───────────────┘ └───────────────┘ └───────────────┘ │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ │
│  │   routes/     │ │   routes/     │ │   routes/     │ │
│  │   hod.py      │ │  director.py  │ │   student.py  │ │
│  └───────────────┘ └───────────────┘ └───────────────┘ │
│                           │                            │
│  ┌────────────────────────▼─────────────────────────┐  │
│  │              AI COMPUTER VISION ENGINE           │  │
│  │  ai/detector.py    ──► YOLOv8 Person/Head Detect │  │
│  │  ai/recognizer.py  ──► DeepFace 128-d Embeddings │  │
│  │  Cosine Similarity ──► Distance Matrix Matching  │  │
│  └──────────────────────────────────────────────────┘  │
│                           │                            │
│  ┌────────────────────────▼─────────────────────────┐  │
│  │              DATABASE & PERSISTENCE              │  │
│  │  SQLite / PostgreSQL (via Flask-SQLAlchemy)      │  │
│  │  Users · Students · Departments · Classes        │  │
│  │  StudentTrainingImages · AttendanceRecords       │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technologies Used |
|---|---|
| **Backend Framework** | Python 3.9+, Flask 3.0, Werkzeug |
| **ORM & Database** | Flask-SQLAlchemy 3.1, SQLite (default) / PostgreSQL |
| **Authentication** | Flask-Login (session-based with bcrypt password hashing) |
| **Object Detection** | Ultralytics YOLOv8 Medium (`yolov8m.pt`) |
| **Face Recognition** | DeepFace, FaceNet (128-d vector embeddings) |
| **Image Processing** | OpenCV (`cv2`), Pillow, NumPy |
| **Data Processing** | Pandas, OpenPyXL, CSV |
| **Frontend UI** | Jinja2 Templates, Vanilla CSS Design System, FontAwesome 6 |
| **Data Visualization** | Chart.js 4.4 |

---

## 📂 Project Structure

```
YOLO_Attend/
├── ai/
│   ├── detector.py             # YOLOv8 face detection & vector extraction
│   └── recognizer.py           # Attendance matching & batch embedding generator
├── routes/
│   ├── admin.py                # Admin portal, student training, staff & dept management
│   ├── auth.py                 # Login, registration, session management
│   ├── teacher.py              # Attendance marking, timetable, manual overrides
│   ├── student.py              # Student dashboard & personal attendance
│   ├── hod.py                  # Departmental oversight & analytics
│   └── director.py             # Executive dashboard & institute analytics
├── templates/
│   ├── base.html               # Master layout with responsive sidebar & theme tokens
│   ├── admin/
│   │   ├── student_training.html # Student AI Training Center (Dataset & YOLO Training)
│   │   ├── student_registration.html # Student applications & verification
│   │   ├── dashboard.html      # Admin overview & system metrics
│   │   ├── analytics.html      # Institutional reports
│   │   ├── staff_log.html      # Faculty management & class division mapping
│   │   ├── approvals.html      # Staff account & subject approval requests
│   │   └── permissions.html    # RBAC permissions matrix
│   ├── teacher/                # Teacher attendance & lecture management views
│   ├── student/                # Student attendance portal
│   ├── hod/                    # HOD department views
│   ├── director/               # Director executive views
│   └── auth/                   # Authentication & login templates
├── uploads/
│   └── training_images/        # Isolated per-student dataset image storage
├── utils/
│   └── auth_utils.py           # Permission helpers & role-based redirection
├── models.py                   # SQLAlchemy database schemas & helper methods
├── app.py                      # Application factory, blueprint registration & seeders
├── config.py                   # Database & application configurations
├── extensions.py               # Shared DB & LoginManager instances
├── download_models.py          # Script to pre-download YOLOv8 weights
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.9+** (Python 3.10 / 3.11 recommended)
- **Git**
- **pip** package manager

### 2. Clone Repository
```bash
git clone https://github.com/your-username/YOLO_Attend.git
cd YOLO_Attend
```

### 3. Create & Activate Virtual Environment
```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Download YOLO Weights & Initialize Models
```bash
python download_models.py
```
*(Alternatively, YOLOv8 will automatically download `yolov8m.pt` upon first execution).*

### 6. Run the Application
```bash
python app.py
```
Access the application in your browser at: **`http://127.0.0.1:5000`**

---

## 🔐 Default Demo Accounts

Upon initial startup, the database is pre-seeded with role-based demo accounts:

| Role | Username | Password | Notes |
|---|---|---|---|
| **Admin** | `utkarshyadav29` | `Rgi@best` | Full Master Admin access |
| **Director** | `DIR001` | `dir123` | Executive institute reports |
| **HOD** | `HOD001` | `hod123` | Head of CSE Department |
| **Teacher** | `TCH001` | `tch123` | Prof. Alan Turing |
| **Student** | `STU101` | `101` | Alex Morgan (Roll: 101) |

---

## 📖 How to Use Student Training

1. Log in as an **Admin** (`utkarshyadav29` / `Rgi@best`).
2. Click **Student Training** in the sidebar.
3. Use the top filters (Department, Class, Status, Search) to locate any student.
4. Click **Manage Photos** on a student card:
   - Drag and drop or browse multiple facial photos.
   - Preview uploaded dataset photos or delete any poor-quality images.
5. Click **Train Student** to extract YOLO + FaceNet embeddings for that student, or click **Train All Students** on the top-right to batch-train the entire institution.
6. Once marked as **Trained**, teachers can immediately upload classroom photos to identify those students during lecture attendance!

---

## 🧪 Testing & Verification

Run the accuracy diagnostic script to test detection and encoding on sample classroom images:
```bash
python test_accuracy.py path/to/classroom_photo.jpg
```

---

## 📄 License
This project is licensed under the **MIT License**.