# 🎓 SmartAttend (`YOLO_Attend`)
### AI-Powered Facial Recognition Attendance & Student Training System

![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)
![YOLOv8](https://img.shields.io/badge/YOLO-v8-orange.svg)
![DeepFace](https://img.shields.io/badge/DeepFace-FaceNet-red.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-Restoration-brightgreen.svg)
![Owner](https://img.shields.io/badge/Owner-srj7042-blueviolet.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)

**SmartAttend** is a full-stack, enterprise-grade AI attendance management platform designed for educational institutions. It automates classroom attendance by detecting and identifying faces in group classroom photographs using **YOLOv8** computer vision, **OpenCV image restoration**, and **DeepFace / FaceNet** biometric embeddings.

---

## 👤 Repository Owner & Maintainer
- **Owner**: **Suraj Jaiswal** ([@srj7042](https://github.com/srj7042))
- **Repository**: [https://github.com/srj7042/YOLO_Attend.git](https://github.com/srj7042/YOLO_Attend.git)

---

## 🌟 Key Features

### 1. 🤖 AI Attendance Marking (YOLOv8 + OpenCV + DeepFace)
- **High-Resolution Crowd Detection**: Uses YOLOv8 Medium (`yolov8m.pt`) with adaptive resolution scaling (`imgsz=1280` or `1536`) to accurately localize students in dense classroom rows.
- **Blur & Low-Light Image Restoration**:
  - **Adaptive Unsharp Masking**: Sharpens blurred photos using unsharp masking ($1.6 \times I - 0.6 \times \text{GaussianBlur}(I)$) based on Laplacian variance blur scoring.
  - **CLAHE Lighting Normalization**: Applies Contrast Limited Adaptive Histogram Equalization on LAB color space to equalize dim lighting.
  - **Bicubic Crop Upscaling**: Automatically rescales small or distant face crops ($<160\times 160\text{px}$) to standard resolution with edge enhancement.
  - **OpenCV Haar Cascade Fallback**: Auto-triggers Haar Cascade frontal face detection if YOLO yields zero boxes on extremely blurry images.
- **Deep Biometric Embeddings**: Generates 128-dimensional L2-normalized facial vectors via FaceNet.
- **Quality-Aware Cosine Matching**: Vectorized matrix dot-product comparison against stored biometrics (Threshold: $\ge 0.55$; Deep Scan $\ge 0.58$).
- **Deep Scan Retry**: Enhanced secondary scan pass with lower detection thresholds (`conf=0.12`) and expanded crop padding (`pad=20`px) for difficult lighting or partial face occlusions.

### 2. 📸 Biometric Training & Image Requirements
- **Student Registration (Training)**:
  - **Minimum Required**: **1 photo** (2–4 photos recommended).
  - **Multi-Stage Augmentation**: Generates 4 L2-normalized embeddings per crop (Original, Horizontal Mirroring, CLAHE Lighting, Unsharp Masking). Even a 1–2 photo upload yields 4–8 distinct biometric profile vectors in the database.
- **Classroom Attendance Marking**:
  - **Minimum Required**: **1 wide-angle classroom photo** (2–3 photos recommended for large lecture halls to prevent student occlusion).

### 3. 🧠 Student AI Training Center (Admin Panel)
- **Dynamic Student Dataset Grid**: View all registered students with real-time biometric training statuses (`Trained`, `Training`, `Not Trained`).
- **Per-Student Photo Management**: Drag-and-drop multiple facial photos per student with isolated storage (`uploads/training_images/student_<id>/`).
- **Individual & Bulk Training**: One-click single student training or batch "Train All Students" across the entire institution.
- **Dynamic Multi-Filters**: Client-side filtering by Department, Class/Division, Training Status, and Search.

### 4. 📋 Student Registration & Verification Workflow
- **Application Queue**: Multi-tab interface separating `Pending Applications`, `Verified Students`, `Add Student`, and `CSV Upload`.
- **Automatic Identity Generation**: Auto-generates official branch registration numbers (`ACSE`, `ACOE`, `AIFT`) and roll numbers upon verification.
- **Bulk CSV Import & Preview**: Validates schema integrity, email/phone uniqueness, and branch assignments.

### 5. 👥 Role-Based Access Control (RBAC)
- **Master Admin**: Institutional oversight, Department & Division management, Staff approvals, Student Training Center, Permissions matrix, and Audit Logging.
- **Director / Dean**: Executive cross-department statistics, faculty performance indicators, and institutional trends.
- **HOD (Head of Department)**: Department-level class performance analytics and subject oversight.
- **Teacher**: Lecture scheduling, classroom image upload & AI attendance processing, manual overrides, discrepancy tracking, and CSV/Excel exports.
- **Student**: Personal attendance ledger, monthly participation charts, and subject-wise breakdown.

### 6. 📊 Analytics & Reporting
- Real-time weekly participation trends powered by **Chart.js**.
- One-click export to **CSV** and **Excel** for division-wise and subject-wise attendance ledgers.

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
│  │  enhance_image_quality ──► Unsharp Mask + CLAHE  │  │
│  │  ai/detector.py        ──► YOLOv8 + Haar Cascade │  │
│  │  ai/recognizer.py      ──► DeepFace FaceNet 128-d│  │
│  │  Cosine Matrix Match   ──► Vectorized Similarity │  │
│  └──────────────────────────────────────────────────┘  │
│                           │                            │
│  ┌────────────────────────▼─────────────────────────┐  │
│  │              DATABASE & PERSISTENCE              │  │
│  │  SQLite / MySQL (via Flask-SQLAlchemy)           │  │
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
| **ORM & Database** | Flask-SQLAlchemy 3.1, SQLite / MySQL |
| **Authentication** | Flask-Login (session-based with bcrypt password hashing) |
| **Object Detection** | Ultralytics YOLOv8 Medium (`yolov8m.pt`) + OpenCV Haar Cascade |
| **Face Recognition** | DeepFace, FaceNet (128-d vector embeddings) |
| **Image Restoration** | OpenCV (`cv2` Unsharp Masking, CLAHE, Laplacian Variance, Bicubic Rescaling), NumPy |
| **Data Processing** | Pandas, OpenPyXL, CSV |
| **Frontend UI** | Jinja2 Templates, Vanilla CSS Design Tokens, FontAwesome 6 |
| **Data Visualization** | Chart.js 4.4 |

---

## 📂 Project Structure

```
YOLO_Attend/
├── ai/
│   ├── detector.py             # YOLOv8 face detection, OpenCV blur restoration & vector extraction
│   └── recognizer.py           # Cosine matching engine & batch embedding generator
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
├── test_accuracy.py            # Quality check & detection benchmark script
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
git clone https://github.com/srj7042/YOLO_Attend.git
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
Access the application in your browser at: **`http://127.0.0.1:3000`**

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
   - Drag and drop or browse 1–4 facial photos per student.
   - Preview uploaded dataset photos or delete poor-quality images.
5. Click **Train Student** to extract YOLO + FaceNet embeddings for that student, or click **Train All Students** on the top-right to batch-train the entire institution.
6. Once marked as **Trained**, teachers can immediately upload classroom photos to identify those students during lecture attendance!

---

## 🧪 Testing & Verification

Run the accuracy diagnostic script to test quality scoring, unsharp blur sharpening, detection, and face encoding on sample classroom images:
```bash
python test_accuracy.py path/to/classroom_photo.jpg
```

---

## 🧑‍💻 Author & Owner

**Suraj Jaiswal** (`srj7042`)  
GitHub: [@srj7042](https://github.com/srj7042)  
Repository: [srj7042/YOLO_Attend](https://github.com/srj7042/YOLO_Attend)

---

## 📄 License
This project is licensed under the **MIT License**.