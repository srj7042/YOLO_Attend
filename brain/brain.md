# SmartAttend System Knowledge Base Index

## Project Overview
SmartAttend is an AI-powered automated classroom attendance management system built with Flask, SQLAlchemy, YOLOv8 Medium (`ultralytics`), and DeepFace (`Facenet`). It supports multi-role access (Admin vs. Teacher), hierarchy management (Department → Class/Division → Subject → Student), automated face detection and facial recognition from classroom bulk photographs, manual override, attendance analytics, and CSV/Excel batch imports.

## Documentation Index

1. **[Architecture & System Overview](file:///Users/surajjaiswal/SmartAttend-main_sujal/brain/architecture.md)**
   - High-level system design, technology stack, directory map, design patterns, and application entry points.
2. **[Data Models & Database Schema](file:///Users/surajjaiswal/SmartAttend-main_sujal/brain/database.md)**
   - Complete ER diagram, SQLAlchemy model schemas (`User`, `Department`, `Class`, `Subject`, `Student`, `AttendanceRecord`, `ApprovalRequest`, `DiscrepancyReport`), relationships, cascading deletes, and JSON embedding storage.
3. **[AI & Computer Vision Engine](file:///Users/surajjaiswal/SmartAttend-main_sujal/brain/ai_vision.md)**
   - YOLOv8 Medium person/face detection, resolution scaling, upper-45% head cropping, DeepFace/Facenet feature extraction, cosine similarity matching, and fallback mechanisms.
4. **[Authentication & Authorization](file:///Users/surajjaiswal/SmartAttend-main_sujal/brain/auth.md)**
   - Flask-Login implementation, session management, password hashing, role-based access control (RBAC), `@admin_required`, `@teacher_required`, and teacher onboarding/approval workflow.
5. **[API & Route Specifications](file:///Users/surajjaiswal/SmartAttend-main_sujal/brain/routes_api.md)**
   - Complete endpoint reference for Auth (`/auth`), Admin (`/admin`), and Teacher (`/teacher`), request/response payloads, URL parameters, and API endpoints.
6. **[Business Workflows & Logic](file:///Users/surajjaiswal/SmartAttend-main_sujal/brain/workflows.md)**
   - Step-by-step algorithms for attendance processing, student photo profiling, access request approvals, batch CSV/Excel student onboarding, and attendance session finalization.
7. **[Frontend & UI System](file:///Users/surajjaiswal/SmartAttend-main_sujal/brain/frontend.md)**
   - Jinja2 templating, inheritance tree (`base.html`), CSS styling system, responsive sidebars, stats cards, modal forms, and client-side JavaScript interactions.
8. **[Student Module Specifications](file:///Users/surajjaiswal/SmartAttend-main_sujal/brain/student_module.md)**
   - Roll number/Student ID authentication, `@student_required` RBAC, personalized attendance dashboard, progress bars, Chart.js metrics, and profile photo handling.
9. **[Security, Performance & Testing](file:///Users/surajjaiswal/SmartAttend-main_sujal/brain/security_performance.md)**
   - Threat vectors, file upload sanitization, thread safety in TensorFlow/DeepFace, model caching, memory management, batch processing, and accuracy verification via `test_accuracy.py`.

## Quick Module Reference

| Component | Path | Description |
| :--- | :--- | :--- |
| **App Core** | [app.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/app.py) | Application factory (`create_app`), global context processors, DB init, demo data seeding |
| **Config** | [config.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/config.py) | Flask & SQLAlchemy configuration settings, upload limits, file extensions |
| **Extensions** | [extensions.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/extensions.py) | Shared singletons (`db`, `login_manager`) |
| **ORM Models** | [models.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/models.py) | SQLAlchemy DB entities and relationships |
| **AI Detector** | [ai/detector.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/ai/detector.py) | YOLOv8 object detection + DeepFace (Facenet) encoding + Cosine matching |
| **AI Recognizer** | [ai/recognizer.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/ai/recognizer.py) | Multi-photo attendance orchestration & student embedding generation |
| **Auth Routes** | [routes/auth.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/routes/auth.py) | `/auth` endpoints: login, registration, logout |
| **Admin Routes** | [routes/admin.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/routes/admin.py) | `/admin` endpoints: dashboard, staff log, approval management, analytics |
| **Teacher Routes** | [routes/teacher.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/routes/teacher.py) | `/teacher` endpoints: dashboard, class manager, photo enrollment, attendance marking |
