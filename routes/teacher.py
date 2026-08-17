from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_login import login_required, current_user
from functools import wraps
from models import User, Class, Subject, Student, AttendanceRecord, ApprovalRequest, Department
from extensions import db
from datetime import datetime, date
import csv, io, json, os, pandas as pd
from werkzeug.utils import secure_filename
from config import Config

teacher_bp = Blueprint('teacher', __name__)

def teacher_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('teacher', 'admin'):
            flash('Teacher access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def get_approved_reqs():
    return ApprovalRequest.query.filter_by(teacher_id=current_user.id, status='approved').all()

@teacher_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    approved_requests = get_approved_reqs()
    pending_req = ApprovalRequest.query.filter_by(teacher_id=current_user.id, status='pending').count()
    
    # Get subjects from approved requests
    subject_ids = [r.subject_id for r in approved_requests]
    # Also add subjects directly assigned to the teacher in the Subject table
    assigned_subject_ids = [s.id for s in current_user.subjects]
    
    all_subject_ids = list(set(subject_ids + assigned_subject_ids))
    subjects = Subject.query.filter(Subject.id.in_(all_subject_ids or [0])).all()
    
    from datetime import timedelta
    today = date.today()
    
    # Weekly data for the chart (Mon - Sun of current week)
    weekly = []
    start_of_week = today - timedelta(days=today.weekday())
    for i in range(7):
        d = start_of_week + timedelta(days=i)
        p = AttendanceRecord.query.filter(AttendanceRecord.subject_id.in_(all_subject_ids or [0]), AttendanceRecord.date == d, AttendanceRecord.status == 'present').count()
        a = AttendanceRecord.query.filter(AttendanceRecord.subject_id.in_(all_subject_ids or [0]), AttendanceRecord.date == d, AttendanceRecord.status == 'absent').count()
        weekly.append({'date': d.strftime('%a'), 'present': p, 'absent': a})
    
    weekly_by_subject = {}
    for s in subjects:
        w_sub = []
        for i in range(7):
            d = start_of_week + timedelta(days=i)
            p = AttendanceRecord.query.filter_by(subject_id=s.id, date=d, status='present').count()
            a = AttendanceRecord.query.filter_by(subject_id=s.id, date=d, status='absent').count()
            w_sub.append({'date': d.strftime('%a'), 'present': p, 'absent': a})
        weekly_by_subject[s.id] = w_sub
    
    subject_stats = []
    for s in subjects:
        total = AttendanceRecord.query.filter_by(subject_id=s.id).count()
        present = AttendanceRecord.query.filter_by(subject_id=s.id, status='present').count()
        pct = round((present / total * 100) if total else 0, 1)
        subject_stats.append({
            'id': s.id,
            'name': s.name,
            'code': s.code,
            'present': present,
            'total': total,
            'pct': pct
        })
    
    today_sessions = AttendanceRecord.query.filter(
        AttendanceRecord.subject_id.in_(all_subject_ids or [0]), 
        AttendanceRecord.date == today
    ).group_by(AttendanceRecord.time_slot, AttendanceRecord.subject_id).count()

    is_approved = current_user.is_active_account

    return render_template('teacher/dashboard.html', 
        subjects=subjects, 
        pending_req=pending_req,
        today_sessions=today_sessions,
        weekly=json.dumps(weekly),
        weekly_by_sub=json.dumps(weekly_by_subject),
        subject_stats=json.dumps(subject_stats),
        is_approved=is_approved)

@teacher_bp.route('/request-access', methods=['GET', 'POST'])
@login_required
@teacher_required
def request_access():
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        class_id = request.form.get('class_id')
        message = request.form.get('message', '')
        existing = ApprovalRequest.query.filter_by(teacher_id=current_user.id, subject_id=subject_id, status='pending').first()
        if existing:
            flash('Pending request already exists for this subject.', 'warning')
        else:
            req = ApprovalRequest(teacher_id=current_user.id, subject_id=subject_id, class_id=class_id, message=message)
            db.session.add(req); db.session.commit()
            flash('Access request submitted successfully.', 'success')
        return redirect(url_for('teacher.dashboard'))
    classes = Class.query.all()
    my_requests = ApprovalRequest.query.filter_by(teacher_id=current_user.id).order_by(ApprovalRequest.created_at.desc()).all()
    return render_template('teacher/request_access.html', classes=classes, my_requests=my_requests)

@teacher_bp.route('/classes')
@teacher_bp.route('/classes/<int:subject_id>')
@login_required
@teacher_required
def classes(subject_id=None):
    approved_requests = get_approved_reqs()
    subject_ids = [r.subject_id for r in approved_requests]
    assigned_subject_ids = [s.id for s in current_user.subjects]
    all_subject_ids = list(set(subject_ids + assigned_subject_ids))
    subjects = Subject.query.filter(Subject.id.in_(all_subject_ids or [0])).all()

    if not subject_id and subjects:
        return redirect(url_for('teacher.classes', subject_id=subjects[0].id))

    subject = Subject.query.get_or_404(subject_id) if subject_id else None
    students = Student.query.filter_by(class_id=subject.class_id).order_by(Student.student_id).all() if subject else []
    
    # Calculate attendance percentages for each student in this subject
    student_data = []
    for s in students:
        total = AttendanceRecord.query.filter_by(student_id=s.id, subject_id=subject_id).count()
        present = AttendanceRecord.query.filter_by(student_id=s.id, subject_id=subject_id, status='present').count()
        pct = round((present / total * 100) if total else 0, 1)
        
        photos_list = []
        folder = os.path.join(Config.UPLOAD_FOLDER, f'student_{s.id}')
        if os.path.exists(folder):
            photos_list = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
        student_data.append({
            'obj': s,
            'pct': pct,
            'photos': photos_list
        })

    is_approved = current_user.is_active_account
    return render_template('teacher/classes.html', subjects=subjects, subject=subject, student_data=student_data, is_approved=is_approved)

@teacher_bp.route('/lectures', methods=['GET', 'POST'])
@login_required
@teacher_required
def lectures():
    if request.method == 'POST':
        payload_str = request.form.get('payload')
        if payload_str:
            import json
            data = json.loads(payload_str)
            
            # Find or Create Department
            dept_name = data.get('dept', 'Unknown Dept')
            dept = Department.query.filter_by(name=dept_name).first()
            if not dept:
                dept = Department(name=dept_name, code=dept_name[:3].upper())
                db.session.add(dept)
                db.session.flush()

            # Find or Create Class
            year_map = {"First Year": 1, "Second Year": 2, "Third Year": 3, "BTech": 4}
            year_val = year_map.get(data.get('year'), 1)
            cls_name = f"{data.get('year')} {dept.code}"
            
            cls = Class.query.filter_by(name=cls_name, section=data.get('division'), department_id=dept.id).first()
            if not cls:
                cls = Class(name=cls_name, section=data.get('division'), year=year_val, department_id=dept.id)
                db.session.add(cls)
                db.session.flush()

            # Find or Create Subject
            subj = Subject.query.filter_by(name=data.get('name'), class_id=cls.id).first()
            if not subj:
                subj = Subject(name=data.get('name'), code=data.get('code'), class_id=cls.id)
                db.session.add(subj)
                db.session.flush()

            # Check if pending request already exists
            existing = ApprovalRequest.query.filter_by(teacher_id=current_user.id, subject_id=subj.id, status='pending').first()
            if not existing:
                req = ApprovalRequest(
                    teacher_id=current_user.id,
                    subject_id=subj.id,
                    class_id=cls.id,
                    note=json.dumps(data.get('dates', [])) # Store the lecture schedules requested
                )
                db.session.add(req)
                db.session.commit()
                flash('Subject and Schedule request sent to Admin for approval.', 'success')
            else:
                flash('You already have a pending request for this subject.', 'warning')
            
            return redirect(url_for('teacher.dashboard'))
            
    departments = Department.query.all()
    is_approved = current_user.is_active_account
    return render_template('teacher/lectures.html', departments=departments, is_approved=is_approved)

@teacher_bp.route('/delete_subject/<int:subject_id>', methods=['POST'])
@login_required
@teacher_required
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    # Due to SQLAlchemy cascade settings, deleting the subject will also delete 
    # its attendance records and approval requests.
    db.session.delete(subject)
    db.session.commit()
    flash(f"Subject '{subject.name}' and all associated data deleted.", "success")
    return redirect(url_for('teacher.classes'))

@teacher_bp.route('/classes/<int:subject_id>/add-student', methods=['POST'])
@login_required
@teacher_required
def add_student(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    class_id = subject.class_id
    student_id = request.form.get('student_id')
    roll_number = request.form.get('roll_number')
    name = request.form.get('name')
    email = request.form.get('email')
    address = request.form.get('address')
    
    if Student.query.filter_by(student_id=student_id, class_id=class_id).first():
        flash('Student ID already exists in this class.', 'error')
    else:
        new_student = Student(
            student_id=student_id, 
            roll_number=roll_number,
            name=name, 
            email=email, 
            address=address,
            class_id=class_id
        )
        db.session.add(new_student)
        db.session.flush()

        # Create user account for student login
        default_pw = roll_number if roll_number else student_id
        student_user = User(
            username=student_id,
            name=name,
            role='student',
            email=email if email else f"{student_id}@student.smartattend.edu",
            student_id=new_student.id,
            is_active_account=True
        )
        student_user.set_password(default_pw)
        db.session.add(student_user)
        db.session.commit()
        flash(f'Student {name} added with student login account created (Password: {default_pw}).', 'success')
    return redirect(url_for('teacher.classes', subject_id=subject_id))

@teacher_bp.route('/classes/edit-student/<int:student_id>', methods=['POST'])
@login_required
@teacher_required
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    student.name = request.form.get('name')
    student.student_id = request.form.get('student_id')
    student.roll_number = request.form.get('roll_number')
    student.email = request.form.get('email')
    student.address = request.form.get('address')
    db.session.commit()
    flash(f'Student {student.name} updated.', 'success')
    return redirect(request.referrer or url_for('teacher.classes'))

@teacher_bp.route('/classes/<int:subject_id>/import-csv', methods=['POST'])
@login_required
@teacher_required
def import_students_csv(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    class_id = subject.class_id
    file = request.files.get('csv_file')
    if not file: flash('No file provided.', 'error'); return redirect(url_for('teacher.classes', subject_id=subject_id))
    
    filename = secure_filename(file.filename)
    try:
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            df = pd.read_excel(file)
        else:
            # Try utf-8 first, fallback to latin-1 for CSVs with special characters
            try:
                # We need to read the data to pass it to pandas if we want to seek back
                data = file.stream.read()
                df = pd.read_csv(io.BytesIO(data), encoding='utf-8')
            except Exception:
                df = pd.read_csv(io.BytesIO(data), encoding='latin-1')
        
        new_ids = []; count = 0
        df.columns = [str(c).strip() for c in df.columns]
        for _, row in df.iterrows():
            # Robust mapping for various possible header names
            def get_val(keys):
                for k in keys:
                    if k in row and pd.notna(row[k]): return str(row[k]).strip()
                return ''

            sid = get_val(['Student_id', 'student_id', 'ID', 'Id'])
            name = get_val(['Name', 'name', 'Student Name', 'Full Name'])
            roll = get_val(['Roll Number', 'roll_number', 'Roll No', 'Roll'])
            email = get_val(['Email', 'email', 'E-mail'])
            address = get_val(['Address', 'address', 'Location'])
            
            if sid and name:
                existing = Student.query.filter_by(student_id=sid, class_id=class_id).first()
                if not existing:
                    new_student = Student(
                        student_id=sid, 
                        name=name, 
                        roll_number=roll,
                        email=email, 
                        address=address,
                        class_id=class_id
                    )
                    db.session.add(new_student)
                    db.session.flush() # Get the ID

                    # Create user login account for student
                    default_pw = roll if roll else sid
                    if not User.query.filter_by(username=sid).first():
                        st_user = User(
                            username=sid,
                            name=name,
                            role='student',
                            email=email if email else f"{sid}@student.smartattend.edu",
                            student_id=new_student.id,
                            is_active_account=True
                        )
                        st_user.set_password(default_pw)
                        db.session.add(st_user)

                    new_ids.append(str(new_student.id))
                    count += 1
        db.session.commit()
        if count > 0:
            flash(f'{count} new students imported successfully.', 'success')
            return redirect(url_for('teacher.classes', subject_id=subject_id, highlight=','.join(new_ids)))
        else:
            flash('Import complete. No new students were found (all records already existed).', 'info')
    except Exception as e:
        flash(f'Error importing file: {str(e)}', 'error')
        
    return redirect(url_for('teacher.classes', subject_id=subject_id))

@teacher_bp.route('/classes/upload-photo/<int:student_id>', methods=['POST'])
@login_required
@teacher_required
def upload_student_photo(student_id):
    student = Student.query.get_or_404(student_id); photos = request.files.getlist('photos')
    saved_paths = []; folder = os.path.join(Config.UPLOAD_FOLDER, f'student_{student_id}'); os.makedirs(folder, exist_ok=True)
    for photo in photos:
        if photo and photo.filename:
            path = os.path.join(folder, secure_filename(photo.filename)); photo.save(path); saved_paths.append(path)
    if saved_paths:
        try:
            from ai.recognizer import generate_face_embeddings
            embeddings = generate_face_embeddings(saved_paths)
            if embeddings:
                existing = student.get_encoding()
                if existing and isinstance(existing[0], (int, float)): existing = [existing]
                student.set_encoding((existing or []) + embeddings)
        except: pass
        student.photo_count = (student.photo_count or 0) + len(saved_paths); db.session.commit()
        return jsonify({'success': True, 'photos': student.photo_count})
    return jsonify({'error': 'No photos saved'}), 400

@teacher_bp.route('/classes/delete-photo/<int:student_id>/<filename>', methods=['POST'])
@login_required
@teacher_required
def delete_student_photo(student_id, filename):
    student = Student.query.get_or_404(student_id)
    folder = os.path.join(Config.UPLOAD_FOLDER, f'student_{student_id}')
    path = os.path.join(folder, secure_filename(filename))
    
    if os.path.exists(path):
        os.remove(path)
        student.photo_count = max(0, (student.photo_count or 0) - 1)
        db.session.commit()
        return jsonify({'success': True, 'photo_count': student.photo_count})
    return jsonify({'error': 'File not found'}), 404

@teacher_bp.route('/mark-attendance', methods=['GET', 'POST'])
@login_required
@teacher_required
def mark_attendance():
    approved_requests = get_approved_reqs()
    approved_subjects = [Subject.query.get(r.subject_id) for r in approved_requests if Subject.query.get(r.subject_id)]
    
    subject_id = request.args.get('subject_id', type=int)
    att_date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # Get approved dates for this subject
    approved_dates = []
    schedules_by_date = {} # To help UI with time slots
    if subject_id:
        for r in approved_requests:
            if r.subject_id == subject_id and r.note:
                try:
                    data = json.loads(r.note)
                    if isinstance(data, list):
                        for item in data:
                            d = item.get('date')
                            if d:
                                approved_dates.append(d)
                                schedules_by_date[d] = item.get('times', [])
                except: pass
    
    att_date = datetime.strptime(att_date_str, '%Y-%m-%d').date()
    # Find slots for currently selected date
    current_slots = schedules_by_date.get(att_date_str, [])
    subject = None
    student_data = []
    is_processed = False
    is_finalized = False
    
    if subject_id:
        subject = Subject.query.get(subject_id)
        if subject:
            students = Student.query.filter_by(class_id=subject.class_id).all()
            records = AttendanceRecord.query.filter_by(subject_id=subject_id, date=att_date).all()
            record_map = {r.student_id: r for r in records}
            
            if records: is_processed = True
            is_finalized = any(r.is_finalized for r in records)
            
            for s in students:
                rec = record_map.get(s.id)
                student_data.append({
                    'obj': s,
                    'is_present': rec.status == 'present' if rec else False,
                    'confidence': int((rec.ai_confidence or 0) * 100) if rec else 0,
                    'method': rec.method if rec else None,
                    'is_finalized': rec.is_finalized if rec else False
                })

    if request.method == 'POST':
        subject_id = request.form.get('subject_id', type=int)
        attendance_date = request.form.get('date')
        lecture_time = request.form.get('time')
        photos = request.files.getlist('photos')
        is_retry = request.form.get('retry') == '1'
        
        if not subject_id or not attendance_date or not photos:
            flash('Please select a subject and upload photos.', 'error')
            return redirect(url_for('teacher.mark_attendance', subject_id=subject_id, date=attendance_date))
            
        subject = Subject.query.get_or_404(subject_id)
        students = Student.query.filter_by(class_id=subject.class_id).all()
        
        session_folder = os.path.join(Config.UPLOAD_FOLDER, 'sessions', f'{subject_id}_{attendance_date}')
        os.makedirs(session_folder, exist_ok=True)
        saved_paths = []
        for photo in photos:
            if photo and photo.filename:
                path = os.path.join(session_folder, secure_filename(photo.filename))
                photo.save(path)
                saved_paths.append(path)
        
        try:
            from ai.recognizer import process_attendance
            results = process_attendance(saved_paths, students, deep_scan=is_retry)
        except Exception as e:
            import traceback
            traceback.print_exc()
            flash(f'AI processing error: {str(e)}. Please try again or use manual entry.', 'error')
            return redirect(url_for('teacher.mark_attendance', subject_id=subject_id, date=attendance_date))
            
        att_date_obj = datetime.strptime(attendance_date, '%Y-%m-%d').date()
        for s in students:
            res = results.get(s.id, {'status': 'absent', 'confidence': 0.0})
            existing = AttendanceRecord.query.filter_by(student_id=s.id, subject_id=subject_id, date=att_date_obj).first()
            
            if existing:
                if not getattr(existing, 'is_finalized', False):
                    existing.status = res['status']
                    existing.ai_confidence = res.get('confidence', 0.0)
                    existing.method = 'yolo' if not is_retry else 'yolo (deep)'
                    existing.time_slot = lecture_time
            else:
                db.session.add(AttendanceRecord(
                    student_id=s.id,
                    subject_id=subject_id,
                    date=att_date_obj,
                    time_slot=lecture_time,
                    status=res['status'],
                    marked_by=current_user.id,
                    method='yolo' if not is_retry else 'yolo (deep)',
                    ai_confidence=res.get('confidence', 0.0)
                ))
        db.session.commit()
        flash('Classroom images processed and attendance marked!' if not is_retry else 'Deep Scan completed with higher precision!', 'success')
        return redirect(url_for('teacher.mark_attendance', subject_id=subject_id, date=attendance_date))

    return render_template('teacher/mark_attendance.html', 
                           approved_subjects=approved_subjects, 
                           approved_dates=approved_dates,
                           current_slots=current_slots,
                           subject=subject, 
                           student_data=student_data, 
                           att_date=att_date_str,
                           is_processed=is_processed,
                           is_finalized=is_finalized,
                           today=datetime.now().strftime('%Y-%m-%d'))

@teacher_bp.route('/finalize-attendance', methods=['POST'])
@login_required
@teacher_required
def finalize_attendance():
    subject_id = request.form.get('subject_id', type=int)
    att_date = request.form.get('date')
    if not subject_id or not att_date:
        return jsonify({'success': False, 'error': 'Missing parameters'})
    
    date_obj = datetime.strptime(att_date, '%Y-%m-%d').date()
    records = AttendanceRecord.query.filter_by(subject_id=subject_id, date=date_obj).all()
    
    for r in records:
        r.is_finalized = True
    db.session.commit()
    
    flash('Attendance session finalized and locked. Analytics updated.', 'success')
    return jsonify({'success': True})

@teacher_bp.route('/records')
@login_required
@teacher_required
def records():
    approved_requests = get_approved_reqs()
    approved_subject_ids = [r.subject_id for r in approved_requests]
    subjects = Subject.query.filter(Subject.id.in_(approved_subject_ids)).all() if approved_subject_ids else []
    
    selected_subject_id = request.args.get('subject_id', type=int)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    # Session History (Unique lecture sessions)
    session_query = db.session.query(
        AttendanceRecord.date, 
        AttendanceRecord.time_slot, 
        AttendanceRecord.subject_id,
        Subject.name.label('subject_name'),
        db.func.count(AttendanceRecord.id).label('total_count'),
        db.func.sum(db.case((AttendanceRecord.status == 'present', 1), else_=0)).label('present_count')
    ).join(Subject).filter(AttendanceRecord.subject_id.in_(approved_subject_ids))
    
    if selected_subject_id:
        session_query = session_query.filter(AttendanceRecord.subject_id == selected_subject_id)
    if from_date:
        session_query = session_query.filter(AttendanceRecord.date >= datetime.strptime(from_date, '%Y-%m-%d').date())
    if to_date:
        session_query = session_query.filter(AttendanceRecord.date <= datetime.strptime(to_date, '%Y-%m-%d').date())
        
    sessions = session_query.group_by(AttendanceRecord.date, AttendanceRecord.time_slot, AttendanceRecord.subject_id).order_by(AttendanceRecord.date.desc()).all()
    
    # Student Summary
    student_data = []
    if selected_subject_id:
        subject = Subject.query.get(selected_subject_id)
        students = Student.query.filter_by(class_id=subject.class_id).all()
        all_records = AttendanceRecord.query.filter_by(subject_id=selected_subject_id).all()
        for s in students:
            s_records = [r for r in all_records if r.student_id == s.id]
            present = sum(1 for r in s_records if r.status == 'present')
            total = len(s_records)
            pct = round((present / total * 100) if total else 0, 1)
            student_data.append({
                'student': s,
                'subject': subject,
                'present': present,
                'total': total,
                'pct': pct
            })

    return render_template('teacher/records.html', 
                           subjects=subjects, 
                           selected_subject=selected_subject_id, 
                           from_date=from_date, 
                           to_date=to_date, 
                           sessions=sessions,
                           records=student_data)

@teacher_bp.route('/delete-session', methods=['POST'])
@login_required
@teacher_required
def delete_session():
    data = request.json
    subject_id = data.get('subject_id')
    date_str = data.get('date')
    time_slot = data.get('time_slot')
    
    if not all([subject_id, date_str]):
        return jsonify({'success': False, 'error': 'Missing parameters'})
        
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Delete all records for this specific session
    AttendanceRecord.query.filter_by(
        subject_id=subject_id, 
        date=date_obj, 
        time_slot=time_slot
    ).delete()
    
    db.session.commit()
    return jsonify({'success': True})

@teacher_bp.route('/records/export')
@login_required
@teacher_required
def export_records():
    approved_requests = get_approved_reqs()
    approved_subject_ids = [r.subject_id for r in approved_requests]
    selected_subject_id = request.args.get('subject_id', type=int)
    if not selected_subject_id or selected_subject_id not in approved_subject_ids:
        flash('Invalid subject.', 'error'); return redirect(url_for('teacher.records'))
    subject = Subject.query.get(selected_subject_id)
    students = Student.query.filter_by(class_id=subject.class_id).all()
    records_q = AttendanceRecord.query.filter_by(subject_id=selected_subject_id).all()
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(['Roll No', 'Name', 'Present', 'Absent', 'Total Lectures', 'Percentage', 'Grade'])
    for s in students:
        s_records = [r for r in records_q if r.student_id == s.id]
        present = sum(1 for r in s_records if r.status == 'present'); total = len(s_records)
        pct = round((present / total * 100) if total else 0, 1)
        writer.writerow([s.student_id, s.name, present, total - present, total, f'{pct}%', 'A' if pct >= 85 else 'B' if pct >= 75 else 'C' if pct >= 60 else 'F'])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name=f'{subject.code or subject.name}_attendance.csv')

@teacher_bp.route('/monthly-report')
@login_required
@teacher_required
def monthly_report():
    approved_requests = get_approved_reqs()
    approved_subject_ids = [r.subject_id for r in approved_requests]
    approved_subjects = Subject.query.filter(Subject.id.in_(approved_subject_ids)).all() if approved_subject_ids else []
    selected_subject_id = request.args.get('subject_id', type=int); month_str = request.args.get('month')
    report_data = None; heatmap_data = {}; student_summary = []
    if selected_subject_id and month_str:
        try:
            month_date = datetime.strptime(month_str, '%Y-%m')
            import calendar; days_in_month = calendar.monthrange(month_date.year, month_date.month)[1]
            subject = Subject.query.get(selected_subject_id)
            students = Student.query.filter_by(class_id=subject.class_id).all()
            month_records = AttendanceRecord.query.filter(AttendanceRecord.subject_id == selected_subject_id, db.extract('year', AttendanceRecord.date) == month_date.year, db.extract('month', AttendanceRecord.date) == month_date.month).all()
            below_75 = 0
            for s in students:
                s_records = [r for r in month_records if r.student_id == s.id]
                present = sum(1 for r in s_records if r.status == 'present'); total = len(s_records)
                pct = round((present / total * 100) if total else 0, 1)
                if pct < 75: below_75 += 1
                student_summary.append({'student_id': s.student_id, 'name': s.name, 'present': present, 'absent': total - present, 'total': total, 'percentage': pct, 'grade': 'A' if pct >= 85 else 'B' if pct >= 75 else 'C' if pct >= 60 else 'F'})
            avg_present = sum(s['present'] for s in student_summary)
            total_possible = len(students) * days_in_month
            avg_rate = round((avg_present / total_possible * 100) if total_possible else 0, 1)
            from collections import defaultdict; daily_counts = defaultdict(int)
            for r in month_records:
                if r.status == 'present': daily_counts[r.date.day] += 1
            heatmap_data = {str(d): daily_counts[d] for d in range(1, days_in_month + 1)}
            report_data = {'subject': subject, 'month': month_date, 'days_in_month': days_in_month, 'total_students': len(students), 'below_75': below_75, 'avg_rate': avg_rate}
        except Exception as e:
            flash(f'Error: {e}', 'error')
    return render_template('teacher/monthly_report.html', approved_subjects=approved_subjects, selected_subject_id=selected_subject_id, month_str=month_str, report_data=report_data, heatmap_data=json.dumps(heatmap_data), student_summary=student_summary)

@teacher_bp.route('/student_photos/<int:student_id>')
@login_required
@teacher_required
def student_photos(student_id):
    student = Student.query.get_or_404(student_id)
    folder = os.path.join(Config.UPLOAD_FOLDER, f'student_{student_id}')
    photos = []
    if os.path.exists(folder):
        photos = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return jsonify({'photos': photos})

@teacher_bp.route('/student_photo/<int:student_id>/<filename>')
def serve_student_photo(student_id, filename):
    folder = os.path.join(Config.UPLOAD_FOLDER, f'student_{student_id}')
    return send_file(os.path.join(folder, filename))

@teacher_bp.route('/api/subject_divisions/<int:subject_id>')
@login_required
@teacher_required
def api_subject_divisions(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    dept = subject.class_ref.department
    related_subjects = Subject.query.join(Class).filter(Subject.name == subject.name, Class.department_id == dept.id).all()
    
    divisions = []
    for s in related_subjects:
        divisions.append({
            'subject_id': s.id,
            'class_id': s.class_id,
            'name': f"{dept.name} - {s.class_ref.section}" if s.class_ref.section else s.class_ref.name
        })
    return jsonify({
        'department_name': dept.name,
        'subject_name': subject.name,
        'divisions': divisions
    })

@teacher_bp.route('/api/approved_schedules/<int:subject_id>')
@login_required
@teacher_required
def api_approved_schedules(subject_id):
    # Find the approved request for this subject and teacher
    req = ApprovalRequest.query.filter_by(teacher_id=current_user.id, subject_id=subject_id, status='approved').first()
    if not req:
        # Check if it was assigned directly (assigned subjects don't have approval requests sometimes)
        subject = Subject.query.get_or_404(subject_id)
        if subject.teacher_id == current_user.id:
            # For assigned subjects, allow any date (or default to current week)
            return jsonify({'dates': [], 'is_unrestricted': True})
        return jsonify({'error': 'Not authorized'}), 403
    
    try:
        # The 'note' field contains the JSON list of schedules/dates
        schedules = json.loads(req.note) if req.note else []
        return jsonify({'schedules': schedules, 'is_unrestricted': False})
    except:
        return jsonify({'schedules': [], 'is_unrestricted': True})

@teacher_bp.route('/api/mark-attendance-manual', methods=['POST'])
@login_required
@teacher_required
def mark_attendance_manual():
    data = request.json
    sid = data.get('student_id')
    sub_id = data.get('subject_id')
    date_str = data.get('date')
    status = data.get('status') # 'present' or 'absent'
    
    if not all([sid, sub_id, date_str, status]):
        return jsonify({'error': 'Missing data'}), 400
        
    att_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    existing = AttendanceRecord.query.filter_by(student_id=sid, subject_id=sub_id, date=att_date).first()
    
    if existing:
        if getattr(existing, 'is_finalized', False):
            return jsonify({'error': 'This session is finalized and locked.'}), 403
        existing.status = status
        existing.is_manual_override = True
    else:
        db.session.add(AttendanceRecord(
            student_id=sid,
            subject_id=sub_id,
            date=att_date,
            status=status,
            marked_by=current_user.id,
            is_manual_override=True,
            method='manual'
        ))
    
    db.session.commit()
    return jsonify({'success': True})
