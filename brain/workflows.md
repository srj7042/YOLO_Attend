# Business Workflows & Core Logic

## 1. Automated Attendance Marking Workflow

```mermaid
flowchart TD
    Start[Teacher navigates to /teacher/mark-attendance] --> Select[Select Subject & Approved Date/Time Slot]
    Select --> Upload[Upload Classroom Bulk Photos]
    Upload --> TriggerAI[POST Request to /teacher/mark-attendance]
    
    TriggerAI --> SaveTemp[Save images to uploads/sessions/subject_date/]
    SaveTemp --> CallAI[Invoke ai.recognizer:process_attendance]
    
    CallAI --> LoadYOLO[Load Lazy Cached YOLOv8 Medium Model]
    LoadYOLO --> DetectPeople[Detect bounding boxes @ imgsz=1280]
    
    loop For each detected person box
        DetectPeople --> CropHead[Crop upper 45% box region with 10px padding]
        CropHead --> ExtractEncoding[DeepFace.represent with Facenet model & opencv backend]
    end
    
    ExtractEncoding --> MatchLoop[Cosine Similarity Match against enrolled Class Students]
    
    alt Match found (Score >= 0.60 standard / 0.65 deep)
        MatchLoop --> SetPresent[Mark Student Present with ai_confidence score]
    else Score < Threshold or Unmatched
        MatchLoop --> SetAbsent[Mark Student Absent with ai_confidence = 0.0]
    end
    
    SetPresent --> UpdateDB[Insert/Update AttendanceRecord table]
    SetAbsent --> UpdateDB
    UpdateDB --> Render[Flash Success Alert & Render Mark Attendance View]
    
    Render --> FinalizeChoice{Teacher Finalizes Session?}
    FinalizeChoice -- Yes --> Lock[POST /teacher/finalize-attendance sets is_finalized=True]
    FinalizeChoice -- No --> ManualAdjust[POST /teacher/api/mark-attendance-manual overrides record]
```

## 2. Student Enrollment & Facial Profiling Workflow

1. **Student Registration**: Teacher adds student manually or via CSV/Excel import (`/teacher/classes/<id>/import-csv`).
2. **Photo Upload (`POST /teacher/classes/upload-photo/<id>`)**:
   - Photos saved to `uploads/student_<id>/`.
   - `ai.recognizer:generate_face_embeddings(saved_paths)` is executed.
   - Embeddings extracted via `detect_and_encode_faces()` (capped at 2 faces per image).
   - Embeddings appended to existing `face_encoding` JSON array in `Student` record.
   - `photo_count` incremented.
3. **Photo Deletion (`POST /teacher/classes/delete-photo/<id>/<filename>`)**:
   - Deletes image file from filesystem, decrements `photo_count`.

## 3. CSV/Excel Batch Student Import Logic

Implemented in [routes/teacher.py:import_students_csv](file:///Users/surajjaiswal/SmartAttend-main_sujal/routes/teacher.py#L261):
1. Accepts `.csv`, `.xlsx`, `.xls`.
2. Reads bytes using `pandas.read_csv()` (with fallback encoding `utf-8` → `latin-1`) or `pandas.read_excel()`.
3. Normalizes column headers (`str.strip()`).
4. Performs flexible header mapping:
   - `student_id`: `['Student_id', 'student_id', 'ID', 'Id']`
   - `name`: `['Name', 'name', 'Student Name', 'Full Name']`
   - `roll_number`: `['Roll Number', 'roll_number', 'Roll No', 'Roll']`
   - `email`: `['Email', 'email', 'E-mail']`
   - `address`: `['Address', 'address', 'Location']`
5. Checks database for existing `student_id` within class to prevent duplicates.
6. Bulk inserts new `Student` records.

## 4. Subject Access & Lecture Schedule Request Lifecycle

1. Teacher submits schedule request via `/teacher/lectures` specifying department, year, division, subject code/name, and lecture dates/times.
2. System auto-creates `Department`, `Class`, and `Subject` if not already present.
3. Creates `ApprovalRequest` record with `status='pending'` and JSON schedule in `note`.
4. Admin views pending requests at `/admin/approvals`.
5. Upon Admin approval (`POST /admin/approve_request/<id>`):
   - `ApprovalRequest.status` updated to `'approved'`.
   - `Subject.teacher_id` linked to teacher ID.
   - Subject unlocked on teacher dashboard and attendance marking views.
