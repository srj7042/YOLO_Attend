from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models import User, Department, Class, Subject, Student, AttendanceRecord, ApprovalRequest, PendingStudent, generate_registration_and_roll_number
from datetime import datetime, date, timedelta
import csv, io, json

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
    return redirect(url_for('admin.student_registration', tab='verified'))

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
    import os
    student = Student.query.get_or_404(student_id)
    files = request.files.getlist('photos')
    all_encodings = student.get_encoding()

    for f in files:
        if f and f.filename:
            path = os.path.join('/tmp', f'student_{student_id}_{f.filename}')
            f.save(path)
            encs = detect_and_encode_faces(path)
            all_encodings.extend(encs)
            os.remove(path)

    student.set_encoding(all_encodings)
    student.photo_count = len(files)
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

    return render_template('admin/staff_log.html', teachers=teachers, dept_stats=dept_stats, dept_by_year=dept_by_year)

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
