from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import User, Class, Subject, Student, AttendanceRecord, Department
from extensions import db
from datetime import datetime, date
import os
from config import Config

student_bp = Blueprint('student', __name__)

def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('Student access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    # Retrieve linked student profile
    student = current_user.student_profile
    if not student:
        # Fallback search by student_id or roll_number matching username
        student = Student.query.filter((Student.student_id == current_user.username) | (Student.roll_number == current_user.username)).first()
    
    if not student:
        flash('Student profile data not linked. Please contact administration.', 'error')
        return render_template('student/dashboard.html', student=None, subject_stats=[], history=[], total_lectures=0, total_present=0, overall_pct=0)

    # Class and Department info
    cls = student.class_ref
    dept = cls.department if cls else None

    # Subjects for student's class
    subjects = Subject.query.filter_by(class_id=student.class_id).all() if cls else []
    
    # Calculate subject-wise attendance
    subject_stats = []
    total_lectures = 0
    total_present = 0

    for subj in subjects:
        records = AttendanceRecord.query.filter_by(student_id=student.id, subject_id=subj.id).all()
        subj_total = len(records)
        subj_present = sum(1 for r in records if r.status == 'present')
        subj_pct = round((subj_present / subj_total * 100) if subj_total else 0, 1)

        teacher_name = subj.teacher.name if subj.teacher else 'Unassigned'

        subject_stats.append({
            'subject': subj,
            'teacher_name': teacher_name,
            'total': subj_total,
            'present': subj_present,
            'absent': subj_total - subj_present,
            'pct': subj_pct
        })
        total_lectures += subj_total
        total_present += subj_present

    overall_pct = round((total_present / total_lectures * 100) if total_lectures else 0, 1)

    # Detailed attendance history log
    records_query = db.session.query(
        AttendanceRecord,
        Subject,
        User
    ).join(Subject, AttendanceRecord.subject_id == Subject.id)\
     .outerjoin(User, Subject.teacher_id == User.id)\
     .filter(AttendanceRecord.student_id == student.id)\
     .order_by(AttendanceRecord.date.desc(), AttendanceRecord.id.desc()).all()

    history = []
    for rec, subj, teacher in records_query:
        history.append({
            'date': rec.date.strftime('%Y-%m-%d'),
            'time_slot': rec.time_slot or 'N/A',
            'subject_name': subj.name,
            'subject_code': subj.code or '',
            'teacher_name': teacher.name if teacher else 'N/A',
            'status': rec.status,
            'method': rec.method or 'N/A',
            'ai_confidence': int((rec.ai_confidence or 0) * 100)
        })

    # Weekly & Monthly chart data for student
    from datetime import timedelta
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    weekly = []
    for i in range(7):
        d = start_of_week + timedelta(days=i)
        p = AttendanceRecord.query.filter_by(student_id=student.id, date=d, status='present').count()
        a = AttendanceRecord.query.filter_by(student_id=student.id, date=d, status='absent').count()
        weekly.append({'date': d.strftime('%a'), 'present': p, 'absent': a})

    # Profile photo filename check
    photo_filename = None
    folder = os.path.join(Config.UPLOAD_FOLDER, f'student_{student.id}')
    if os.path.exists(folder):
        photos = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if photos:
            photo_filename = photos[0]

    return render_template(
        'student/dashboard.html',
        student=student,
        cls=cls,
        dept=dept,
        subject_stats=subject_stats,
        history=history,
        total_lectures=total_lectures,
        total_present=total_present,
        total_absent=total_lectures - total_present,
        overall_pct=overall_pct,
        weekly=weekly,
        photo_filename=photo_filename
    )

@student_bp.route('/photo')
@login_required
@student_required
def get_photo():
    student = current_user.student_profile
    if not student:
        student = Student.query.filter((Student.student_id == current_user.username) | (Student.roll_number == current_user.username)).first()
    
    if student:
        folder = os.path.join(Config.UPLOAD_FOLDER, f'student_{student.id}')
        if os.path.exists(folder):
            photos = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if photos:
                return send_file(os.path.join(folder, photos[0]))
    
    return redirect('https://ui-avatars.com/api/?name=' + (current_user.name or 'Student'))

@student_bp.route('/change-password', methods=['POST'])
@login_required
@student_required
def change_password():
    current_pw = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm_pw = request.form.get('confirm_password', '')

    if not current_user.check_password(current_pw):
        flash('Incorrect current password.', 'error')
        return redirect(url_for('student.dashboard'))

    if len(new_pw) < 6:
        flash('New password must be at least 6 characters long.', 'error')
        return redirect(url_for('student.dashboard'))

    if new_pw != confirm_pw:
        flash('New password and confirmation do not match.', 'error')
        return redirect(url_for('student.dashboard'))

    current_user.set_password(new_pw)
    db.session.commit()
    flash('Password changed successfully!', 'success')
    return redirect(url_for('student.dashboard'))
