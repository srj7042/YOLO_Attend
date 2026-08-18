from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import User, Class, Subject, Student, AttendanceRecord, ApprovalRequest, Department
from utils.auth_utils import role_required, permission_required, user_has_permission
from datetime import datetime, date, timedelta
import json

hod_bp = Blueprint('hod', __name__)

@hod_bp.route('/dashboard')
@login_required
@role_required('hod', 'admin')
def dashboard():
    dept_name = current_user.department or 'Computer Science & Engineering'
    dept = Department.query.filter_by(name=dept_name).first()
    if not dept:
        dept = Department.query.first()

    dept_id = dept.id if dept else None

    # Classes in HOD department
    classes = Class.query.filter_by(department_id=dept_id).all() if dept_id else Class.query.all()
    class_ids = [c.id for c in classes]

    # Students in department classes
    students = Student.query.filter(Student.class_id.in_(class_ids or [0])).all()
    total_students = len(students)

    # Teachers in HOD department
    teachers = User.query.filter_by(role='teacher', department=dept_name).all()
    total_teachers = len(teachers)

    # Subjects in department classes
    subjects = Subject.query.filter(Subject.class_id.in_(class_ids or [0])).all()
    total_subjects = len(subjects)
    subj_ids = [s.id for s in subjects]

    # Attendance records in department subjects
    today = date.today()
    today_attendance_count = AttendanceRecord.query.filter(
        AttendanceRecord.subject_id.in_(subj_ids or [0]),
        AttendanceRecord.date == today
    ).count()

    today_present = AttendanceRecord.query.filter(
        AttendanceRecord.subject_id.in_(subj_ids or [0]),
        AttendanceRecord.date == today,
        AttendanceRecord.status == 'present'
    ).count()

    today_pct = round((today_present / today_attendance_count * 100) if today_attendance_count else 0, 1)

    # Pending teacher approval requests in department
    pending_approvals = ApprovalRequest.query.filter(
        ApprovalRequest.class_id.in_(class_ids or [0]),
        ApprovalRequest.status == 'pending'
    ).all()

    # Weekly attendance trend for department
    start_of_week = today - timedelta(days=today.weekday())
    weekly = []
    for i in range(7):
        d = start_of_week + timedelta(days=i)
        p = AttendanceRecord.query.filter(
            AttendanceRecord.subject_id.in_(subj_ids or [0]),
            AttendanceRecord.date == d,
            AttendanceRecord.status == 'present'
        ).count()
        a = AttendanceRecord.query.filter(
            AttendanceRecord.subject_id.in_(subj_ids or [0]),
            AttendanceRecord.date == d,
            AttendanceRecord.status == 'absent'
        ).count()
        weekly.append({'date': d.strftime('%a'), 'present': p, 'absent': a})

    return render_template(
        'hod/dashboard.html',
        dept_name=dept_name,
        department=dept,
        total_students=total_students,
        total_teachers=total_teachers,
        total_subjects=total_subjects,
        total_classes=len(classes),
        today_attendance_count=today_attendance_count,
        today_pct=today_pct,
        teachers=teachers,
        students=students[:10],
        subjects=subjects,
        pending_approvals=pending_approvals,
        weekly=json.dumps(weekly)
    )

@hod_bp.route('/approve-teacher/<int:req_id>', methods=['POST'])
@login_required
@role_required('hod', 'admin')
def approve_teacher(req_id):
    req = ApprovalRequest.query.get_or_404(req_id)
    req.status = 'approved'
    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.utcnow()
    
    # Assign subject to teacher
    subj = req.subject
    if subj:
        subj.teacher_id = req.teacher_id

    db.session.commit()
    flash(f'Request approved for {req.teacher.name}.', 'success')
    return redirect(url_for('hod.dashboard'))
