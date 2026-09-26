from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models import User, Department, Class, Subject, Student, StudentTrainingImage, AttendanceRecord, ApprovalRequest, PendingStudent, AuditLog, generate_registration_and_roll_number
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
import csv, io, json, os, uuid
from config import Config
from utils.image_utils import save_and_optimize_student_photo, get_or_create_thumbnail, is_allowed_image


admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_students = Student.query.count()
    total_classes = Class.query.count()
    total_teachers = User.query.filter_by(role='teacher').count()
    pending_approvals = ApprovalRequest.query.filter_by(status='pending').count()
    today = date.today()
    today_records = AttendanceRecord.query.filter_by(date=today).count()

    # Weekly attendance data for chart
    weekly = []
    for i in range(7):
        d = today - timedelta(days=6-i)
        present = AttendanceRecord.query.filter_by(date=d, status='present').count()
        absent = AttendanceRecord.query.filter_by(date=d, status='absent').count()
        weekly.append({'date': d.strftime('%a'), 'present': present, 'absent': absent})

    recent_approvals = ApprovalRequest.query.filter_by(status='pending').order_by(ApprovalRequest.created_at.desc()).limit(5).all()

    # Monthly data from real DB
    months_data = []
    for i in range(6, 0, -1):
        month_start = date.today().replace(day=1) - timedelta(days=30 * (i-1))
        month_label = month_start.strftime('%b')
        total_m = AttendanceRecord.query.filter(db.func.strftime('%Y-%m', AttendanceRecord.date) == month_start.strftime('%Y-%m')).count()
        present_m = AttendanceRecord.query.filter(db.func.strftime('%Y-%m', AttendanceRecord.date) == month_start.strftime('%Y-%m'), AttendanceRecord.status=='present').count()
        avg = round(present_m / total_m * 100, 1) if total_m else 0
        months_data.append({'month': month_label, 'avg': avg})

    # Real faculty benchmark data from DB
    faculty_stats = []
    teachers = User.query.filter_by(role='teacher', is_active_account=True).all()
    for t in teachers:
        subj_ids = [s.id for s in t.subjects]
        if not subj_ids:
            continue
        for s in t.subjects:
            total = AttendanceRecord.query.filter_by(subject_id=s.id).count()
            present = AttendanceRecord.query.filter_by(subject_id=s.id, status='present').count()
            score = round(present / total * 100, 1) if total else 0
            faculty_stats.append({'name': t.name, 'subject': s.name.upper(), 'score': score})
        if len(faculty_stats) >= 4:
            break

    # Student Block Metrics & Roster
    pending_students_count = PendingStudent.query.filter_by(status='pending').count()
    face_enrolled_count = Student.query.filter(Student.photo_count > 0).count()
    branches = ['AIML', 'Computer', 'IT']
    branch_counts = {b: Student.query.filter(Student.branch.ilike(f'%{b}%')).count() for b in branches}

    recent_students_raw = Student.query.order_by(Student.created_at.desc()).limit(10).all()
    recent_students_list = []
    for s in recent_students_raw:
        total_att = AttendanceRecord.query.filter_by(student_id=s.id).count()
        pres_att = AttendanceRecord.query.filter_by(student_id=s.id, status='present').count()
        pct = round((pres_att / total_att * 100), 1) if total_att else 0
        recent_students_list.append({
            'id': s.id,
            'name': s.name,
            'student_id': s.student_id or s.registration_number or f'STU{s.id:03d}',
            'roll_number': s.roll_number or '-',
            'email': s.email or '-',
            'branch': s.branch or 'General',
            'class_name': s.class_ref.full_name if s.class_ref else 'Unassigned',
            'has_face': bool((s.photo_count or 0) > 0 or s.has_embeddings),
            'photo_count': s.image_count,
            'attendance_pct': pct,
            'total_attendance': total_att
        })

    return render_template('admin/dashboard.html',
        total_students=total_students,
        total_classes=total_classes,
        total_teachers=total_teachers,
        pending_approvals=pending_approvals,
        today_records=today_records,
        weekly=json.dumps(weekly),
        monthly=json.dumps(months_data),
        recent_approvals=recent_approvals,
        faculty_stats=faculty_stats,
        recent_students=recent_students_list,
        pending_students_count=pending_students_count,
        face_enrolled_count=face_enrolled_count,
        branch_counts=branch_counts,
        institute_name="GH Raisoni College of Engineering & Management"
    )

@admin_bp.route('/classes', methods=['GET', 'POST'])
@login_required
@admin_required
def classes():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_dept':
            dept = Department(name=request.form['dept_name'], code=request.form['dept_code'].upper())
            db.session.add(dept)
            db.session.commit()
            flash('Department added successfully', 'success')
        elif action == 'add_class':
            cls = Class(name=request.form['class_name'], section=request.form.get('section',''),
                        year=int(request.form.get('year', 1)), department_id=int(request.form['dept_id']))
            db.session.add(cls)
            db.session.commit()
            flash('Class added successfully', 'success')
        elif action == 'add_subject':
            subj = Subject(name=request.form['subj_name'], code=request.form.get('subj_code',''),
                           class_id=int(request.form['class_id']), credits=int(request.form.get('credits',4)))
            db.session.add(subj)
            db.session.commit()
            flash('Subject added successfully', 'success')
        elif action == 'assign_teacher':
            subj = Subject.query.get(int(request.form['subject_id']))
            subj.teacher_id = int(request.form['teacher_id']) if request.form['teacher_id'] else None
            db.session.commit()
            flash('Teacher assigned successfully', 'success')
        return redirect(url_for('admin.classes'))

    departments = Department.query.all()
    teachers = User.query.filter_by(role='teacher').all()
    return redirect(url_for('admin.staff_log'))

@admin_bp.route('/delete_department/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_department(id):
    dept = Department.query.get_or_404(id)
    # Recursively handle classes and students if needed, or just delete the dept
    # To prevent foreign key errors, we might need to handle dependencies
    db.session.delete(dept)
    db.session.commit()
    flash(f'Department "{dept.name}" deleted.', 'success')
    return redirect(url_for('admin.staff_log'))

@admin_bp.route('/add_class', methods=['POST'])
@login_required
@admin_required
def add_class():
    dept_id = request.form.get('dept_id')
    section = request.form.get('section', '').strip()
    dept = Department.query.get(dept_id)
    if not dept or not section:
        flash('Invalid department or division name.', 'error')
        return redirect(url_for('admin.staff_log'))
    
    # User requested: "divison will also contain the same name of the department only the divion will be changed"
    class_name = f"{dept.name}"
    cls = Class(name=class_name, section=section, department_id=dept.id, year=1)
    db.session.add(cls)
    db.session.commit()
    flash(f'Division "{section}" added to {dept.name}.', 'success')
    return redirect(url_for('admin.staff_log'))

@admin_bp.route('/delete_class/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_class(id):
    cls = Class.query.get_or_404(id)
    db.session.delete(cls)
    db.session.commit()
    flash(f'Division "{cls.section}" deleted.', 'success')
    return redirect(url_for('admin.staff_log'))

@admin_bp.route('/remove_faculty/<int:id>', methods=['POST'])
@login_required
@admin_required
def remove_faculty(id):
    user = User.query.get_or_404(id)
    # "authority of faculty will be taken... whole details... remain but it will not be a faculty"
    user.role = 'guest' 
    user.is_active_account = False
    db.session.commit()
    flash(f'Faculty status removed for {user.name}. Data preserved.', 'success')
    return redirect(url_for('admin.staff_log'))

@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    return render_template('admin/settings.html')

@admin_bp.route('/approvals', methods=['GET', 'POST'])
@login_required
@admin_required
def approvals():
    if request.method == 'POST':
        action = request.form.get('action')
        req_type = request.form.get('req_type')

        if req_type == 'teacher':
            teacher_id = int(request.form.get('teacher_id'))
            teacher = User.query.get(teacher_id)
            if teacher:
                if action == 'approve':
                    teacher.is_active_account = True
                    db.session.commit()
                    flash(f"Teacher {teacher.name}'s account approved.", "success")
                elif action == 'reject':
                    # Instead of deleting, we can just set a status or role
                    teacher.role = 'rejected'
                    db.session.commit()
                    flash(f"Teacher {teacher.name}'s account rejected.", "success")
        else:
            # Subject Approval Logic
            req_id = int(request.form.get('request_id'))
            req = ApprovalRequest.query.get(req_id)
            if req:
                req.status = 'approved' if action == 'approve' else 'rejected'
                req.reviewed_by = current_user.id
                req.reviewed_at = datetime.utcnow()
                if action == 'approve':
                    req.subject.teacher_id = req.teacher_id
                db.session.commit()
                flash(f'Request {req.status} successfully', 'success')
                
        return redirect(url_for('admin.approvals'))

    pending_teachers = User.query.filter_by(role='teacher', is_active_account=False).all()
    history_teachers = User.query.filter(User.role.in_(['teacher', 'rejected']), (User.is_active_account == True) | (User.role == 'rejected')).all()
    pending = ApprovalRequest.query.filter_by(status='pending').order_by(ApprovalRequest.created_at.desc()).all()
    history = ApprovalRequest.query.filter(ApprovalRequest.status != 'pending').order_by(ApprovalRequest.created_at.desc()).limit(20).all()
    return render_template('admin/approvals.html', pending=pending, history=history, pending_teachers=pending_teachers, history_teachers=history_teachers)


@admin_bp.route('/departments', methods=['POST'])
@login_required
@admin_required
def add_department():
    name = request.form.get('dept_name', '').strip()
    code = request.form.get('dept_code', '').strip().upper()
    year = int(request.form.get('dept_year', 1))
    if not name or not code:
        flash('Department name and code are required.', 'error')
        return redirect(url_for('admin.staff_log'))
    if Department.query.filter_by(name=name, year=year).first():
        flash(f'Department "{name}" for that year already exists.', 'warning')
        return redirect(url_for('admin.staff_log'))
    dept = Department(name=name, code=code, year=year)
    db.session.add(dept)
    db.session.commit()
    year_labels = {1: 'First Year', 2: 'Second Year', 3: 'Third Year', 4: 'BTech/Final Year'}
    flash(f'Department "{name}" ({year_labels.get(year, "")}) created successfully.', 'success')
    return redirect(url_for('admin.staff_log'))

@admin_bp.route('/add_subject', methods=['POST'])
@login_required
@admin_required
def add_subject():
    subj_name = request.form.get('subj_name', '').strip()
    subj_code = request.form.get('subj_code', '').strip().upper()
    class_id = request.form.get('class_id')
    teacher_id = request.form.get('teacher_id')
    credits = request.form.get('credits', 4)

    if not subj_name or not class_id:
        flash('Subject name and Division are required.', 'error')
        return redirect(url_for('admin.staff_log'))

    cls = Class.query.get(class_id)
    if not cls:
        flash('Invalid Division selected.', 'error')
        return redirect(url_for('admin.staff_log'))

    if not subj_code:
        words = [w[0] for w in subj_name.split() if w]
        code_prefix = "".join(words)[:4].upper() or "SUB"
        subj_code = f"{code_prefix}101"

    subj = Subject(
        name=subj_name,
        code=subj_code,
        class_id=int(class_id),
        credits=int(credits) if credits else 4,
        teacher_id=int(teacher_id) if teacher_id and teacher_id.isdigit() else None
    )
    db.session.add(subj)
    db.session.commit()
    flash(f'Subject "{subj_name}" ({subj_code}) added successfully for {cls.full_name}.', 'success')
    return redirect(url_for('admin.staff_log'))

@admin_bp.route('/student-registration')
@login_required
@admin_required
def student_registration():
    active_tab = request.args.get('tab', 'pending')
    classes = Class.query.all()
    pending_students = PendingStudent.query.filter_by(status='pending').order_by(PendingStudent.created_at.desc()).all()
    verified_students = Student.query.order_by(Student.created_at.desc()).all()
    rejected_students = PendingStudent.query.filter_by(status='rejected').order_by(PendingStudent.verified_at.desc()).all()

    pending_count = len(pending_students)
    verified_count = len(verified_students)
    rejected_count = len(rejected_students)

    return render_template('admin/student_registration.html',
        active_tab=active_tab,
        classes=classes,
        pending_students=pending_students,
        verified_students=verified_students,
        rejected_students=rejected_students,
        pending_count=pending_count,
        verified_count=verified_count,
        rejected_count=rejected_count
    )

@admin_bp.route('/student-registration/add-single', methods=['POST'])
@login_required
@admin_required
def add_single_student():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()
    branch = request.form.get('branch', '').strip()
    class_id = request.form.get('class_id', type=int)
    address = request.form.get('address', '').strip()

    if not name or not email or not branch:
        flash('Name, Email, and Branch are required fields.', 'error')
        return redirect(url_for('admin.student_registration', tab='add'))

    if Student.query.filter_by(email=email).first() or PendingStudent.query.filter_by(email=email, status='pending').first():
        flash(f'A student or application with email "{email}" already exists.', 'error')
        return redirect(url_for('admin.student_registration', tab='add'))

    if phone and (Student.query.filter_by(phone=phone).first() or PendingStudent.query.filter_by(phone=phone, status='pending').first()):
        flash(f'A student or application with phone "{phone}" already exists.', 'error')
        return redirect(url_for('admin.student_registration', tab='add'))

    pending = PendingStudent(
        name=name,
        email=email,
        phone=phone,
        branch=branch,
        class_id=class_id,
        address=address,
        status='pending'
    )
    db.session.add(pending)
    db.session.commit()
    flash(f'Student application for "{name}" submitted to Pending queue for Admin verification.', 'success')
    return redirect(url_for('admin.student_registration', tab='pending'))

@admin_bp.route('/student-registration/preview-csv', methods=['POST'])
@login_required
@admin_required
def preview_csv():
    file = request.files.get('csv_file')
    if not file or not file.filename.endswith('.csv'):
        return jsonify({'error': 'Please upload a valid .csv file'}), 400

    stream = io.StringIO(file.stream.read().decode('utf-8-sig'))
    reader = csv.DictReader(stream)
    
    valid_rows = []
    error_rows = []
    seen_emails = set()

    for idx, row in enumerate(reader, start=1):
        name = row.get('name', '').strip()
        email = row.get('email', '').strip().lower()
        phone = row.get('phone', '').strip()
        branch = row.get('branch', '').strip()
        address = row.get('address', '').strip()

        row_errors = []
        if not name:
            row_errors.append('Missing Name')
        if not email:
            row_errors.append('Missing Email')
        elif email in seen_emails:
            row_errors.append('Duplicate Email in CSV')
        elif Student.query.filter_by(email=email).first() or PendingStudent.query.filter_by(email=email, status='pending').first():
            row_errors.append('Email already registered in system')
        
        if not branch:
            row_errors.append('Missing Branch')

        if phone and (Student.query.filter_by(phone=phone).first() or PendingStudent.query.filter_by(phone=phone, status='pending').first()):
            row_errors.append('Phone already registered')

        if email:
            seen_emails.add(email)

        item = {
            'row_num': idx,
            'name': name,
            'email': email,
            'phone': phone,
            'branch': branch,
            'address': address
        }

        if row_errors:
            item['errors'] = ', '.join(row_errors)
            error_rows.append(item)
        else:
            valid_rows.append(item)

    return jsonify({
        'valid_rows': valid_rows,
        'error_rows': error_rows,
        'total_valid': len(valid_rows),
        'total_errors': len(error_rows)
    })

@admin_bp.route('/student-registration/import-csv', methods=['POST'])
@login_required
@admin_required
def import_csv():
    file = request.files.get('csv_file')
    class_id = request.form.get('class_id', type=int)

    if not file or not file.filename.endswith('.csv'):
        flash('Please upload a valid CSV file.', 'error')
        return redirect(url_for('admin.student_registration', tab='csv'))

    stream = io.StringIO(file.stream.read().decode('utf-8-sig'))
    reader = csv.DictReader(stream)
    
    count = 0
    skipped = 0

    for row in reader:
        name = row.get('name', '').strip()
        email = row.get('email', '').strip().lower()
        phone = row.get('phone', '').strip()
        branch = row.get('branch', '').strip()
        address = row.get('address', '').strip()

        if not name or not email or not branch:
            skipped += 1
            continue

        if Student.query.filter_by(email=email).first() or PendingStudent.query.filter_by(email=email, status='pending').first():
            skipped += 1
            continue

        pending = PendingStudent(
            name=name,
            email=email,
            phone=phone,
            branch=branch,
            class_id=class_id,
            address=address,
            status='pending'
        )
        db.session.add(pending)
        count += 1

    db.session.commit()
    flash(f'Successfully imported {count} student records to Pending Queue ({skipped} skipped due to validation/duplicates).', 'success')
    return redirect(url_for('admin.student_registration', tab='pending'))

@admin_bp.route('/student-registration/view/<int:id>')
@login_required
@admin_required
def view_pending_student(id):
    p = PendingStudent.query.get_or_404(id)
    cls_name = p.class_ref.full_name if p.class_ref else 'Unassigned'
    return jsonify({
        'id': p.id,
        'name': p.name,
        'email': p.email,
        'phone': p.phone or 'N/A',
        'branch': p.branch,
        'class_name': cls_name,
        'class_id': p.class_id,
        'address': p.address or 'N/A',
        'created_at': p.created_at.strftime('%Y-%m-%d %H:%M'),
        'status': p.status
    })

@admin_bp.route('/student-registration/verify/<int:id>', methods=['POST'])
@login_required
@admin_required
def verify_student(id):
    pending = PendingStudent.query.get_or_404(id)
    if pending.status != 'pending':
        flash('This student application has already been processed.', 'warning')
        return redirect(url_for('admin.student_registration', tab='pending'))

    class_id = request.form.get('class_id', type=int) or pending.class_id
    if not class_id:
        default_cls = Class.query.first()
        class_id = default_cls.id if default_cls else None

    if not class_id:
        flash('Cannot verify student: No class exists in system to assign.', 'error')
        return redirect(url_for('admin.student_registration', tab='pending'))

    # Generate Registration Number & Roll Number
    reg_number, roll_number = generate_registration_and_roll_number(pending.branch, class_id)

    # 1. Create active Student record
    student = Student(
        student_id=reg_number,
        registration_number=reg_number,
        roll_number=roll_number,
        name=pending.name,
        branch=pending.branch,
        class_id=class_id,
        email=pending.email,
        phone=pending.phone,
        address=pending.address
    )
    db.session.add(student)
    db.session.flush()

    # 2. Create User account for student login
    student_user = User(
        username=reg_number,
        name=pending.name,
        email=pending.email,
        role='student',
        student_id=student.id,
        is_active_account=True
    )
    student_user.set_password('password123')
    db.session.add(student_user)

    # 3. Update PendingStudent record
    pending.status = 'verified'
    pending.verified_at = datetime.utcnow()
    pending.verified_by_id = current_user.id
    pending.generated_reg_number = reg_number
    pending.generated_roll_number = roll_number

    db.session.commit()

    flash(f'✅ Student {pending.name} verified! Reg No: {reg_number} | Roll No: {roll_number} | Default Password: password123', 'success')
    return redirect(url_for('admin.student_registration', tab='pending'))

@admin_bp.route('/student-registration/reject/<int:id>', methods=['POST'])
@login_required
@admin_required
def reject_student(id):
    pending = PendingStudent.query.get_or_404(id)
    reason = request.form.get('reason', 'Application details did not meet requirements').strip()

    pending.status = 'rejected'
    pending.rejection_reason = reason
    pending.verified_at = datetime.utcnow()
    pending.verified_by_id = current_user.id

    db.session.commit()
    flash(f'Student application for {pending.name} rejected.', 'info')
    return redirect(url_for('admin.student_registration', tab='pending'))


@admin_bp.route('/upload_photo/<int:student_id>', methods=['POST'])
@login_required
@admin_required
def upload_photo(student_id):
    from ai.detector import detect_and_encode_faces
    student = Student.query.get_or_404(student_id)
    files = request.files.getlist('photos')
    if not files or len(files) == 0:
        return jsonify({'success': False, 'error': 'No photos provided.'}), 400

    upload_dir = os.path.join(Config.UPLOAD_FOLDER, 'training_images', f'student_{student.id}')
    all_encodings = student.get_encoding()
    saved_images_count = 0

    for f in files:
        if not f or not f.filename or not is_allowed_image(f.filename):
            continue

        try:
            opt_path, thumb_path, unique_name = save_and_optimize_student_photo(f, upload_dir)
            train_img = StudentTrainingImage(
                student_id=student.id,
                filename=unique_name,
                filepath=opt_path
            )
            db.session.add(train_img)
            saved_images_count += 1

            encs = detect_and_encode_faces(opt_path)
            if encs:
                all_encodings.extend(encs)
        except Exception as e:
            print(f"[WARN] Error optimizing or encoding face from {f.filename}: {e}")

    student.set_encoding(all_encodings)
    db.session.flush()
    student.photo_count = StudentTrainingImage.query.filter_by(student_id=student.id).count()
    if student.has_embeddings:
        student.training_status = 'Trained'
    db.session.commit()
    return jsonify({'success': True, 'count': len(all_encodings)})

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    from sqlalchemy import func
    classes = Class.query.all()
    class_id = request.args.get('class_id', type=int)

    # Overall stats
    total_records = AttendanceRecord.query.count()
    present_count = AttendanceRecord.query.filter_by(status='present').count()
    overall_pct = round(present_count / total_records * 100, 1) if total_records else 0

    # Per-class breakdown
    class_stats = []
    for cls in classes:
        student_ids = [s.id for s in cls.students]
        if not student_ids:
            continue
        total = AttendanceRecord.query.filter(AttendanceRecord.student_id.in_(student_ids)).count()
        present = AttendanceRecord.query.filter(AttendanceRecord.student_id.in_(student_ids), AttendanceRecord.status=='present').count()
        
        subjects_data = []
        colors = ["var(--brand)", "var(--accent)", "#D6C3EB", "#2DA84F", "#FF9800", "#9C27B0"]
        c_idx = 0
        for subj in cls.subjects:
            s_tot = AttendanceRecord.query.filter(AttendanceRecord.subject_id==subj.id, AttendanceRecord.student_id.in_(student_ids)).count()
            s_pres = AttendanceRecord.query.filter(AttendanceRecord.subject_id==subj.id, AttendanceRecord.student_id.in_(student_ids), AttendanceRecord.status=='present').count()
            if s_tot > 0:
                s_pct = round((s_pres/s_tot)*100, 1)
                subjects_data.append({'name': subj.name, 'val': s_pct, 'color': colors[c_idx % len(colors)], 'weight': f"{s_tot} sessions"})
                c_idx += 1

        overall_cls_pct = round(present/total*100,1) if total else 0
        class_stats.append({
            'name': cls.full_name, 'total': total, 'present': present,
            'pct': overall_cls_pct,
            'overall': f"{overall_cls_pct}%",
            'subjects': subjects_data
        })

    # Faculty stats
    faculty_stats = []
    teachers = User.query.filter_by(role='teacher', is_active_account=True).all()
    for t in teachers:
        subj_ids = [s.id for s in t.subjects]
        if not subj_ids:
            continue
        tot_m = AttendanceRecord.query.filter(AttendanceRecord.subject_id.in_(subj_ids)).count()
        if tot_m > 0:
            pres_m = AttendanceRecord.query.filter(AttendanceRecord.subject_id.in_(subj_ids), AttendanceRecord.status=='present').count()
            score = round(pres_m / tot_m * 100, 1)
            faculty_stats.append({
                'name': t.name,
                'initials': t.name[:2].upper() if t.name else 'T',
                'dept': t.department or 'General',
                'total_sessions': tot_m,
                'score': score
            })

    # Sort faculty by score descending
    faculty_stats.sort(key=lambda x: x['score'], reverse=True)

    return render_template('admin/analytics.html', class_stats=json.dumps(class_stats),
                           overall_pct=overall_pct, total_records=total_records, present_count=present_count,
                           classes=classes, faculty_stats=faculty_stats)

@admin_bp.route('/staff_log', methods=['GET', 'POST'])
@login_required
@admin_required
def staff_log():
    if request.method == 'POST':
        t = User(username=request.form['username'], name=request.form['name'], role='teacher',
                 email=request.form.get('email',''), department=request.form.get('department',''),
                 employee_id=request.form.get('employee_id',''))
        t.set_password(request.form['password'])
        db.session.add(t)
        db.session.commit()
        flash('Teacher account created', 'success')
        return redirect(url_for('admin.staff_log'))
    teachers = User.query.filter_by(role='teacher').all()
    departments = Department.query.all()
    
    dept_stats = []
    for d in departments:
        cls_list = Class.query.filter_by(department_id=d.id).all()
        cls_count = len(cls_list)
        stu_count = Student.query.join(Class).filter(Class.department_id==d.id).count()
        # Gather all subjects under this department
        dept_subjects = []
        for c in cls_list:
            for s in c.subjects:
                if s.name not in [ds['name'] for ds in dept_subjects]:
                    dept_subjects.append({'name': s.name, 'code': s.code})
        dept_stats.append({
            'id': d.id,
            'code': d.code,
            'name': d.name,
            'year': d.year or 1,
            'classes': cls_count,
            'students': stu_count,
            'subjects': dept_subjects
        })

    # Group by year for display
    year_labels = {1: 'First Year', 2: 'Second Year', 3: 'Third Year', 4: 'BTech / Final Year'}
    dept_by_year = {}
    for yr in [1, 2, 3, 4]:
        dept_by_year[yr] = {'label': year_labels[yr], 'depts': [d for d in dept_stats if d['year'] == yr]}

    all_classes = Class.query.order_by(Class.name, Class.section).all()
    return render_template('admin/staff_log.html', teachers=teachers, dept_stats=dept_stats, dept_by_year=dept_by_year, all_classes=all_classes)

@admin_bp.route('/get_divisions/<int:dept_id>')
@login_required
@admin_required
def get_divisions(dept_id):
    classes = Class.query.filter_by(department_id=dept_id).all()
    return jsonify([{'id': c.id, 'section': c.section} for c in classes])

@admin_bp.route('/get_subjects/<int:class_id>')
@login_required
@admin_required
def get_subjects(class_id):
    subjects = Subject.query.filter_by(class_id=class_id).all()
    return jsonify([{'id': s.id, 'name': s.name, 'code': s.code} for s in subjects])

@admin_bp.route('/get_students/<int:class_id>/<int:subject_id>')
@login_required
@admin_required
def get_students_data(class_id, subject_id):
    students = Student.query.filter_by(class_id=class_id).order_by(Student.student_id).all()
    result = []
    for s in students:
        total = AttendanceRecord.query.filter_by(student_id=s.id, subject_id=subject_id).count()
        present = AttendanceRecord.query.filter_by(student_id=s.id, subject_id=subject_id, status='present').count()
        pct = round((present / total * 100) if total else 0, 1)
        result.append({
            'student_id': s.student_id,
            'roll': s.roll_number or '-',
            'name': s.name,
            'email': s.email or '-',
            'present': present,
            'absent': total - present,
            'total': total,
            'pct': pct
        })
    return jsonify(result)

@admin_bp.route('/export_students/<int:class_id>/<int:subject_id>')
@login_required
@admin_required
def export_division_students(class_id, subject_id):
    from flask import send_file
    subject = Subject.query.get_or_404(subject_id)
    cls = Class.query.get_or_404(class_id)
    students = Student.query.filter_by(class_id=class_id).order_by(Student.student_id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID', 'Roll No', 'Name', 'Email', 'Present', 'Absent', 'Total', 'Attendance %'])
    for s in students:
        total = AttendanceRecord.query.filter_by(student_id=s.id, subject_id=subject_id).count()
        present = AttendanceRecord.query.filter_by(student_id=s.id, subject_id=subject_id, status='present').count()
        pct = round((present / total * 100) if total else 0, 1)
        writer.writerow([s.student_id, s.roll_number or '', s.name, s.email or '', present, total - present, total, f'{pct}%'])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{cls.section}_{subject.name}_students.csv'
    )

@admin_bp.route('/permissions')
@login_required
@admin_required
def permissions():
    from utils.auth_utils import DEFAULT_ROLE_PERMISSIONS
    from models import Permission
    
    # Generate list of permissions
    all_codes = sorted(list(DEFAULT_ROLE_PERMISSIONS['admin']))
    permissions_list = [{'code': code, 'name': code.replace('_', ' ').title()} for code in all_codes]

    return render_template(
        'admin/permissions.html',
        permissions_list=permissions_list,
        admin_perms=DEFAULT_ROLE_PERMISSIONS['admin'],
        director_perms=DEFAULT_ROLE_PERMISSIONS['director'],
        hod_perms=DEFAULT_ROLE_PERMISSIONS['hod'],
        teacher_perms=DEFAULT_ROLE_PERMISSIONS['teacher'],
        student_perms=DEFAULT_ROLE_PERMISSIONS['student']
    )

@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    from models import AuditLog
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('admin/audit_logs.html', logs=logs)


# =====================================================================
# STUDENT TRAINING MODULE ROUTES
# =====================================================================

@admin_bp.route('/student-training')
@login_required
@admin_required
def student_training():
    """Main Student Training page displaying student cards, stats, and dynamic filters."""
    students = Student.query.order_by(Student.name.asc()).all()
    departments = Department.query.order_by(Department.name.asc()).all()
    classes = Class.query.order_by(Class.name.asc()).all()

    # Dynamic metrics from DB
    total_students = len(students)
    trained_students = len([s for s in students if s.status_label == 'Trained'])
    not_trained_students = total_students - trained_students
    total_photos = sum(s.image_count for s in students)

    # Collect dynamic unique department names and class names from students & records
    dept_names = sorted(list(set(d.name for d in departments if d.name) | set(s.department_name for s in students if s.department_name)))
    class_names = sorted(list(set(c.full_name for c in classes if c.full_name) | set(s.class_name for s in students if s.class_name)))

    return render_template('admin/student_training.html',
        students=students,
        departments=departments,
        classes=classes,
        dept_names=dept_names,
        class_names=class_names,
        total_students=total_students,
        trained_students=trained_students,
        not_trained_students=not_trained_students,
        total_photos=total_photos
    )


@admin_bp.route('/student-training/student/<int:student_id>/images')
@login_required
@admin_required
def get_student_training_images(student_id):
    """Fetch all uploaded training photos for a specific student."""
    student = Student.query.get_or_404(student_id)
    images = StudentTrainingImage.query.filter_by(student_id=student.id).order_by(StudentTrainingImage.uploaded_at.desc()).all()

    return jsonify({
        'student_id': student.id,
        'student_name': student.name,
        'student_code': student.student_id or student.registration_number or f'STU{student.id:04d}',
        'roll_number': student.roll_number or '-',
        'department': student.department_name,
        'class_name': student.class_name,
        'training_status': student.status_label,
        'has_embeddings': student.has_embeddings,
        'embedding_count': len(student.get_encoding()),
        'photo_count': len(images),
        'images': [{
            'id': img.id,
            'filename': img.filename,
            'url': url_for('admin.get_training_photo', image_id=img.id),
            'uploaded_at': img.uploaded_at.strftime('%d %b %Y, %H:%M')
        } for img in images]
    })


@admin_bp.route('/student-training/student/<int:student_id>/upload', methods=['POST'])
@login_required
@admin_required
def upload_student_training_images(student_id):
    """Handle multi-photo upload for an individual student with WebP optimization and thumbnails."""
    student = Student.query.get_or_404(student_id)
    files = request.files.getlist('photos')

    if not files or len(files) == 0:
        return jsonify({'success': False, 'message': 'No photo files were provided.'}), 400

    upload_dir = os.path.join(Config.UPLOAD_FOLDER, 'training_images', f'student_{student.id}')
    saved_count = 0
    new_images = []

    for f in files:
        if not f or not f.filename or not is_allowed_image(f.filename):
            continue

        try:
            opt_path, thumb_path, unique_name = save_and_optimize_student_photo(f, upload_dir)
            train_img = StudentTrainingImage(
                student_id=student.id,
                filename=unique_name,
                filepath=opt_path
            )
            db.session.add(train_img)
            db.session.flush()

            saved_count += 1
            new_images.append({
                'id': train_img.id,
                'filename': train_img.filename,
                'url': url_for('admin.get_training_photo', image_id=train_img.id),
                'uploaded_at': train_img.uploaded_at.strftime('%d %b %Y, %H:%M')
            })
        except Exception as e:
            print(f"[WARN] Failed to optimize and save photo {f.filename}: {e}")

    # Update student photo count
    total_imgs = StudentTrainingImage.query.filter_by(student_id=student.id).count()
    student.photo_count = total_imgs
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Successfully uploaded and optimized {saved_count} photo(s) for {student.name}.',
        'saved_count': saved_count,
        'photo_count': total_imgs,
        'training_status': student.status_label,
        'has_embeddings': student.has_embeddings,
        'new_images': new_images
    })


@admin_bp.route('/student-training/student/<int:student_id>/delete-image/<int:image_id>', methods=['POST'])
@login_required
@admin_required
def delete_student_training_image(student_id, image_id):
    """Delete a specific training photo for a student."""
    student = Student.query.get_or_404(student_id)
    image = StudentTrainingImage.query.filter_by(id=image_id, student_id=student.id).first_or_404()

    # Remove file from disk
    if os.path.exists(image.filepath):
        try:
            os.remove(image.filepath)
        except Exception as e:
            print(f"[WARN] Could not remove photo file {image.filepath}: {e}")

    db.session.delete(image)
    db.session.commit()

    remaining_count = StudentTrainingImage.query.filter_by(student_id=student.id).count()
    student.photo_count = remaining_count

    # If no photos remain, reset training status and face encoding
    if remaining_count == 0:
        student.training_status = 'Not Trained'
        student.face_encoding = None

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Photo deleted successfully.',
        'remaining_count': remaining_count,
        'training_status': student.status_label,
        'has_embeddings': student.has_embeddings
    })


@admin_bp.route('/student-training/student/<int:student_id>/train', methods=['POST'])
@login_required
@admin_required
def train_student(student_id):
    """
    Optimized YOLO-based student face training:
    - Preprocesses and validates 4-5 uploaded images.
    - Generates realistic classroom augmentations (mirroring, CLAHE, illumination).
    - Extracts L2 normalized DeepFace FaceNet embeddings.
    - Suppresses duplicate vectors to optimize memory & inference speed.
    - Persists embeddings against the student in the database.
    - Returns real measured training quality and consistency metrics.
    """
    student = Student.query.get_or_404(student_id)
    images = StudentTrainingImage.query.filter_by(student_id=student.id).all()

    if not images:
        return jsonify({
            'success': False,
            'message': f'No training photos found for {student.name}. Please upload 4–5 photos first.',
            'status': student.status_label,
            'has_embeddings': student.has_embeddings
        }), 400

    image_paths = [img.filepath for img in images if os.path.exists(img.filepath)]
    if not image_paths:
        student.training_status = 'Not Trained'
        student.face_encoding = None
        db.session.commit()
        return jsonify({
            'success': False,
            'message': 'Uploaded image files are missing from storage. Please re-upload.',
            'status': 'Not Trained',
            'has_embeddings': False
        }), 400

    student.training_status = 'Training'
    db.session.commit()

    print(f"[YOLO-TRAIN] Starting training for Student ID {student.id} ({student.name}). Image count: {len(image_paths)}")

    try:
        from ai.detector import train_student_biometrics
        train_result = train_student_biometrics(image_paths, max_embeddings=15)

        if train_result.get('success') and len(train_result.get('embeddings', [])) > 0:
            embeddings = train_result['embeddings']
            metrics = train_result.get('metrics', {})

            print(f"[YOLO-TRAIN] Generated {len(embeddings)} biometric embeddings for Student ID {student.id}. Persisting to DB...")

            student.set_encoding(embeddings)
            student.photo_count = len(image_paths)
            student.training_status = 'Trained'

            db.session.commit()
            db.session.refresh(student)

            # Verification: ensure embeddings actually stored and retrievable
            stored_enc = student.get_encoding()
            if not stored_enc or len(stored_enc) == 0:
                raise ValueError("Database verification failed: face_encoding column is empty after commit.")

            print(f"[YOLO-TRAIN-SUCCESS] Student ID {student.id} successfully trained! Persisted {len(stored_enc)} embeddings. has_embeddings={student.has_embeddings}")

            db.session.add(AuditLog(
                user_id=current_user.id,
                username=current_user.username,
                action='YOLO_OPTIMIZED_TRAIN_STUDENT',
                description=(
                    f'Trained optimized YOLO model for {student.name} ({student.student_id}). '
                    f'Images: {len(image_paths)} | Vectors: {len(embeddings)} | '
                    f'Intra-Consistency: {metrics.get("intra_consistency", 0.0)} | '
                    f'Status: {metrics.get("quality_status", "Optimal")}'
                )
            ))
            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'✅ Successfully trained {student.name}! Extracted {len(embeddings)} optimized biometric embeddings from {len(image_paths)} photos.',
                'status': 'Trained',
                'has_embeddings': True,
                'embedding_count': len(embeddings),
                'photo_count': len(image_paths),
                'metrics': metrics,
                'validation_reports': train_result.get('validation_reports', [])
            })
        else:
            student.training_status = 'Not Trained'
            student.face_encoding = None
            db.session.commit()
            print(f"[YOLO-TRAIN-WARN] No valid face biometrics extracted for Student ID {student.id}")
            return jsonify({
                'success': False,
                'message': f'Could not extract valid face biometrics from {student.name}\'s photos. Please ensure clear frontal face photos.',
                'status': 'Not Trained',
                'has_embeddings': False,
                'embedding_count': 0,
                'validation_reports': train_result.get('validation_reports', [])
            }), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        student.training_status = 'Not Trained'
        student.face_encoding = None
        db.session.commit()
        return jsonify({'success': False, 'message': f'Training error: {str(e)}', 'status': 'Not Trained', 'has_embeddings': False}), 500


@admin_bp.route('/student-training/train-all', methods=['POST'])
@login_required
@admin_required
def train_all_students():
    """
    Batch train all students who have uploaded training images using the optimized pipeline.
    """
    students = Student.query.all()
    if not students:
        return jsonify({'success': False, 'message': 'No students found in the database to train.'}), 400

    from ai.detector import train_student_biometrics

    trained_count = 0
    skipped_no_photos = 0
    failed_detection = 0
    total_vectors = 0

    print(f"[YOLO-BATCH-TRAIN] Starting batch training across {len(students)} students...")

    for student in students:
        images = StudentTrainingImage.query.filter_by(student_id=student.id).all()
        image_paths = [img.filepath for img in images if os.path.exists(img.filepath)]

        if not image_paths:
            skipped_no_photos += 1
            continue

        try:
            train_res = train_student_biometrics(image_paths, max_embeddings=15)
            if train_res.get('success') and len(train_res.get('embeddings', [])) > 0:
                embeddings = train_res['embeddings']
                student.set_encoding(embeddings)
                student.photo_count = len(image_paths)
                student.training_status = 'Trained'
                trained_count += 1
                total_vectors += len(embeddings)
                print(f"  [OK] Trained student {student.id} ({student.name}): {len(embeddings)} vectors")
            else:
                student.training_status = 'Not Trained'
                student.face_encoding = None
                failed_detection += 1
                print(f"  [FAIL] Could not extract faces for student {student.id} ({student.name})")
        except Exception as e:
            print(f"  [ERR] Error batch training student {student.id} ({student.name}): {e}")
            student.training_status = 'Not Trained'
            student.face_encoding = None
            failed_detection += 1

    db.session.commit()

    db.session.add(AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action='YOLO_BATCH_TRAIN_ALL_STUDENTS',
        description=f'Batch YOLO training: {trained_count} trained ({total_vectors} total biometric vectors), {skipped_no_photos} skipped without photos, {failed_detection} failed.'
    ))
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Batch training completed! {trained_count} student(s) successfully trained ({total_vectors} total optimized biometric vectors generated).',
        'trained_count': trained_count,
        'skipped_count': skipped_no_photos,
        'failed_count': failed_detection,
        'total_vectors': total_vectors
    })



@admin_bp.route('/student-training/student/<int:student_id>/validate-images')
@login_required
@admin_required
def validate_student_images(student_id):
    """Validate uploaded images of a student for blur, lighting, resolution."""
    student = Student.query.get_or_404(student_id)
    images = StudentTrainingImage.query.filter_by(student_id=student.id).all()

    from ai.detector import validate_image_quality

    reports = []
    for img in images:
        if os.path.exists(img.filepath):
            report = validate_image_quality(img.filepath)
            report['image_id'] = img.id
            report['filename'] = img.filename
            report['url'] = url_for('admin.get_training_photo', image_id=img.id)
            reports.append(report)

    overall_valid = all(r.get('is_valid', False) for r in reports) if reports else False
    return jsonify({
        'student_id': student.id,
        'student_name': student.name,
        'total_images': len(reports),
        'overall_valid': overall_valid,
        'reports': reports
    })



@admin_bp.route('/student-training/photo/<int:image_id>')
@login_required
@admin_required
def get_training_photo(image_id):
    """Serve a specific training photo image file."""
    image = StudentTrainingImage.query.get_or_404(image_id)
    if not os.path.exists(image.filepath):
        return jsonify({'error': 'Image file not found on disk'}), 404
    return send_file(image.filepath)


@admin_bp.route('/student-training/student/<int:student_id>/avatar')
@login_required
def get_student_avatar(student_id):
    """Serve a student's optimized thumbnail avatar, or fallback to ui-avatars."""
    student = Student.query.get_or_404(student_id)
    latest_img = StudentTrainingImage.query.filter_by(student_id=student.id).order_by(StudentTrainingImage.uploaded_at.desc()).first()
    if latest_img and os.path.exists(latest_img.filepath):
        thumb = get_or_create_thumbnail(latest_img.filepath)
        if thumb and os.path.exists(thumb):
            return send_file(thumb, mimetype='image/webp')
        return send_file(latest_img.filepath)

    # Check folder on disk directly in case images exist without DB entry
    for folder_rel in [os.path.join('training_images', f'student_{student.id}'), f'student_{student.id}']:
        folder = os.path.join(Config.UPLOAD_FOLDER, folder_rel)
        if os.path.isdir(folder):
            files = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and not f.startswith('thumb_')]
            if files:
                full_path = os.path.join(folder, files[-1])
                thumb = get_or_create_thumbnail(full_path)
                if thumb and os.path.exists(thumb):
                    return send_file(thumb, mimetype='image/webp')
                return send_file(full_path)

    return redirect(f"https://ui-avatars.com/api/?name={student.name}&background=0F204C&color=fff&size=128")


