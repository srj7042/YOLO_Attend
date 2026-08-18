from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import User, Class, Subject, Student, AttendanceRecord, Department, ApprovalRequest
from utils.auth_utils import role_required, permission_required
from datetime import datetime, date, timedelta
import json

director_bp = Blueprint('director', __name__)

@director_bp.route('/dashboard')
@login_required
@role_required('director', 'admin')
def dashboard():
    total_departments = Department.query.count()
    total_students = Student.query.count()
    total_teachers = User.query.filter_by(role='teacher').count()
    total_hods = User.query.filter_by(role='hod').count()
    total_classes = Class.query.count()

    today = date.today()
    today_records = AttendanceRecord.query.filter_by(date=today).count()
    today_present = AttendanceRecord.query.filter_by(date=today, status='present').count()
    overall_attendance_pct = round((today_present / today_records * 100) if today_records else 0, 1)

    # Department breakdown statistics
    departments = Department.query.all()
    dept_stats = []
    for dept in departments:
        cls_ids = [c.id for c in dept.classes]
        st_count = Student.query.filter(Student.class_id.in_(cls_ids or [0])).count()
        subj_ids = [s.id for s in Subject.query.filter(Subject.class_id.in_(cls_ids or [0])).all()]
        att_total = AttendanceRecord.query.filter(AttendanceRecord.subject_id.in_(subj_ids or [0])).count()
        att_present = AttendanceRecord.query.filter(
            AttendanceRecord.subject_id.in_(subj_ids or [0]),
            AttendanceRecord.status == 'present'
        ).count()
        pct = round((att_present / att_total * 100) if att_total else 0, 1)

        hod_user = User.query.filter_by(role='hod', department=dept.name).first()

        dept_stats.append({
            'id': dept.id,
            'name': dept.name,
            'code': dept.code,
            'students_count': st_count,
            'classes_count': len(dept.classes),
            'attendance_pct': pct,
            'hod_name': hod_user.name if hod_user else 'Unassigned'
        })

    # Weekly attendance trend institutional
    start_of_week = today - timedelta(days=today.weekday())
    weekly = []
    for i in range(7):
        d = start_of_week + timedelta(days=i)
        p = AttendanceRecord.query.filter_by(date=d, status='present').count()
        a = AttendanceRecord.query.filter_by(date=d, status='absent').count()
        weekly.append({'date': d.strftime('%a'), 'present': p, 'absent': a})

    return render_template(
        'director/dashboard.html',
        total_departments=total_departments,
        total_students=total_students,
        total_teachers=total_teachers,
        total_hods=total_hods,
        total_classes=total_classes,
        overall_attendance_pct=overall_attendance_pct,
        dept_stats=dept_stats,
        weekly=json.dumps(weekly),
        institute_name="GH Raisoni College of Engineering & Management"
    )
