# Data Models & Database Schema

## Entity Relationship Diagram

```mermaid
erDiagram
    User ||--o{ Subject : "teaches"
    User ||--o{ ApprovalRequest : "requests (teacher)"
    User ||--o{ ApprovalRequest : "reviews (admin)"
    Department ||--o{ Class : "contains"
    Class ||--o{ Student : "enrolls"
    Class ||--o{ Subject : "has"
    Subject ||--o{ AttendanceRecord : "tracks"
    Student ||--o{ AttendanceRecord : "has"
    AttendanceRecord ||--o{ DiscrepancyReport : "has"

    User {
        int id PK
        string username UK
        string password_hash
        string role "admin|teacher"
        string name
        string email UK
        string department
        string employee_id UK
        boolean is_active_account
    }

    Department {
        int id PK
        string name
        string code UK
        int year
    }

    Class {
        int id PK
        string name
        string section
        int year
        int department_id FK
    }

    Subject {
        int id PK
        string name
        string code
        int class_id FK
        int teacher_id FK
        int credits
    }

    Student {
        int id PK
        string student_id UK
        string roll_number
        string name
        int class_id FK
        text face_encoding "JSON Embeddings Array"
        int photo_count
    }

    AttendanceRecord {
        int id PK
        int student_id FK
        int subject_id FK
        date date
        string time_slot
        string status "present|absent"
        float ai_confidence
        string method "yolo|yolo (deep)|manual"
        boolean is_manual_override
        boolean is_finalized
    }

    ApprovalRequest {
        int id PK
        int teacher_id FK
        int subject_id FK
        int class_id FK
        string status "pending|approved|rejected"
        text note "JSON Lecture Schedules"
    }

    DiscrepancyReport {
        int id PK
        int attendance_id FK
        string raised_by
        text reason
        string status "open|resolved"
    }
```

## Model Schema Specifications

### 1. `User` ([models.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/models.py#L7))
- `id` (Integer, Primary Key)
- `username` (String(80), Unique, Mandatory)
- `password_hash` (String(255), Mandatory)
- `role` (String(20), Mandatory): `'admin'` or `'teacher'`
- `name` (String(120), Mandatory)
- `email` (String(120), Unique)
- `department` (String(100))
- `employee_id` (String(50), Unique)
- `avatar_initials` (String(4))
- `is_active_account` (Boolean, default=True): Admin approval indicator for teachers.
- **Relationships**: `approval_requests` (Cascade delete-orphan).

### 2. `Department` ([models.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/models.py#L34))
- `id` (Integer, Primary Key)
- `name` (String(100), Mandatory)
- `code` (String(20), Unique, Mandatory)
- `year` (Integer, default=1)
- **Relationships**: `classes` (Cascade delete-orphan).

### 3. `Class` ([models.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/models.py#L44))
- `id` (Integer, Primary Key)
- `name` (String(100), Mandatory): e.g. "First Year Computer Science"
- `section` (String(10)): Division (e.g. "A", "B")
- `year` (Integer)
- `department_id` (Integer, ForeignKey `departments.id`)
- **Relationships**: `students` (Cascade delete-orphan), `subjects` (Cascade delete-orphan).
- **Properties**: `full_name` returns `"{name} - {section}"`.

### 4. `Subject` ([models.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/models.py#L61))
- `id` (Integer, Primary Key)
- `name` (String(150), Mandatory)
- `code` (String(30))
- `class_id` (Integer, ForeignKey `classes.id`)
- `teacher_id` (Integer, ForeignKey `users.id`, Nullable)
- `credits` (Integer, default=4)
- **Relationships**: `teacher`, `attendance_records` (Cascade delete-orphan).

### 5. `Student` ([models.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/models.py#L75))
- `id` (Integer, Primary Key)
- `student_id` (String(30), Unique, Mandatory): External ID/PRN
- `roll_number` (String(20))
- `name` (String(120), Mandatory)
- `class_id` (Integer, ForeignKey `classes.id`)
- `email` (String(120))
- `phone` (String(20))
- `address` (String(250))
- `face_encoding` (Text): Serialized JSON list of 128-dimensional float embeddings `[[float,...], ...]`.
- `photo_count` (Integer, default=0)
- **Methods**: `set_encoding(list)` (JSON dumps), `get_encoding()` (JSON loads), property `has_face_data`.

### 6. `AttendanceRecord` ([models.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/models.py#L104))
- `id` (Integer, Primary Key)
- `student_id` (Integer, ForeignKey `students.id`)
- `subject_id` (Integer, ForeignKey `subjects.id`)
- `date` (Date, Mandatory)
- `time_slot` (String(20)): e.g. "10:00-11:00"
- `status` (String(10), Mandatory): `'present'` or `'absent'`
- `marked_by` (Integer, ForeignKey `users.id`)
- `ai_confidence` (Float): Similarity score (0.0 to 1.0)
- `method` (String(20)): `'yolo'`, `'yolo (deep)'`, or `'manual'`
- `is_manual_override` (Boolean, default=False)
- `is_finalized` (Boolean, default=False): Locked session status.

### 7. `ApprovalRequest` ([models.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/models.py#L121))
- `id` (Integer, Primary Key)
- `teacher_id` (Integer, ForeignKey `users.id`)
- `subject_id` (Integer, ForeignKey `subjects.id`)
- `class_id` (Integer, ForeignKey `classes.id`)
- `status` (String(20), default='pending'): `'pending'`, `'approved'`, `'rejected'`
- `note` (Text): JSON string containing requested lecture schedule dates/times.
- `reviewed_by` (Integer, ForeignKey `users.id`)
- `reviewed_at` (DateTime)

### 8. `DiscrepancyReport` ([models.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/models.py#L138))
- `id` (Integer, Primary Key)
- `attendance_id` (Integer, ForeignKey `attendance_records.id`)
- `raised_by` (String(120))
- `reason` (Text)
- `status` (String(20), default='open'): `'open'`, `'resolved'`
- `resolved_by` (Integer, ForeignKey `users.id`)
