from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'teacher'
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True)
    department = db.Column(db.String(100))
    employee_id = db.Column(db.String(50), unique=True)
    avatar_initials = db.Column(db.String(4))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active_account = db.Column(db.Boolean, default=True)

    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    student_profile = db.relationship('Student', backref='user_account', foreign_keys=[student_id])
    approval_requests = db.relationship('ApprovalRequest', backref='teacher', lazy=True, cascade="all, delete-orphan", foreign_keys='ApprovalRequest.teacher_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_initials(self):
        parts = self.name.split()
        return ''.join(p[0].upper() for p in parts[:2])


class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    year = db.Column(db.Integer, default=1)  # 1=FY, 2=SY, 3=TY, 4=BTech
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    classes = db.relationship('Class', backref='department', lazy=True, cascade="all, delete-orphan")


class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    section = db.Column(db.String(10))
    year = db.Column(db.Integer)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    students = db.relationship('Student', backref='class_ref', lazy=True, cascade="all, delete-orphan")
    subjects = db.relationship('Subject', backref='class_ref', lazy=True, cascade="all, delete-orphan")

    @property
    def full_name(self):
        return f"{self.name} - {self.section}" if self.section else self.name


class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(30))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    credits = db.Column(db.Integer, default=4)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teacher = db.relationship('User', backref='subjects', foreign_keys=[teacher_id])
    attendance_records = db.relationship('AttendanceRecord', backref='subject', lazy=True, cascade="all, delete-orphan")


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(30), unique=True, nullable=False) # Registration Number (e.g. ACSE00001)
    registration_number = db.Column(db.String(30), unique=True)
    roll_number = db.Column(db.String(20))
    name = db.Column(db.String(120), nullable=False)
    branch = db.Column(db.String(50)) # 'AIML', 'Computer', 'IT'
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20), unique=True)
    address = db.Column(db.String(250))  # Full address field (City, State)
    face_encoding = db.Column(db.Text)  # JSON list of embeddings
    photo_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy=True, cascade="all, delete-orphan")

    def set_encoding(self, encodings_list):
        self.face_encoding = json.dumps(encodings_list)

    def get_encoding(self):
        if self.face_encoding:
            return json.loads(self.face_encoding)
        return []

    @property
    def has_face_data(self):
        return self.photo_count > 0


class PendingStudent(db.Model):
    __tablename__ = 'pending_students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True)
    branch = db.Column(db.String(50), nullable=False) # 'AIML', 'Computer', 'IT'
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    address = db.Column(db.String(250))
    status = db.Column(db.String(20), default='pending') # 'pending', 'verified', 'rejected'
    rejection_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    generated_reg_number = db.Column(db.String(30))
    generated_roll_number = db.Column(db.String(20))

    class_ref = db.relationship('Class', backref='pending_students', lazy=True)
    verifier = db.relationship('User', foreign_keys=[verified_by_id])


def get_branch_prefix(branch_name):
    branch_clean = (branch_name or '').strip().upper()
    if 'AIML' in branch_clean or 'AI' in branch_clean or 'MACHINE' in branch_clean:
        return 'ACSE'
    elif 'COMP' in branch_clean or 'CSE' in branch_clean or 'COE' in branch_clean:
        return 'ACOE'
    elif 'IT' in branch_clean or 'INFO' in branch_clean:
        return 'AIFT'
    return 'ACSE'

def generate_registration_and_roll_number(branch_name, class_id=None):
    """
    Generates branch Registration Number (ACSEXXXXX, ACOEXXXXX, AIFTXXXXX)
    and class sequential Roll Number.
    """
    prefix = get_branch_prefix(branch_name)
    
    # Find existing registration numbers with this prefix across Student & PendingStudent tables
    existing_reg_nums = set()
    
    # From active students
    st_regs = Student.query.filter(
        (Student.registration_number.like(f"{prefix}%")) | (Student.student_id.like(f"{prefix}%"))
    ).all()
    for s in st_regs:
        reg = s.registration_number or s.student_id
        if reg and reg.startswith(prefix):
            existing_reg_nums.add(reg)

    # From pending students
    p_regs = PendingStudent.query.filter(PendingStudent.generated_reg_number.like(f"{prefix}%")).all()
    for p in p_regs:
        if p.generated_reg_number:
            existing_reg_nums.add(p.generated_reg_number)

    # Find highest sequence
    max_seq = 0
    for reg in existing_reg_nums:
        seq_str = reg[len(prefix):]
        if seq_str.isdigit():
            max_seq = max(max_seq, int(seq_str))
            
    next_seq = max_seq + 1
    reg_number = f"{prefix}{next_seq:05d}"
    
    # Roll number generation
    if class_id:
        st_count = Student.query.filter_by(class_id=class_id).count()
        p_count = PendingStudent.query.filter_by(class_id=class_id, status='verified').count()
        roll_number = str(st_count + p_count + 101)
    else:
        tot_count = Student.query.count()
        roll_number = str(tot_count + 101)

    return reg_number, roll_number


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(20))  # e.g. "10:00-11:00"
    status = db.Column(db.String(10), nullable=False)  # 'present' or 'absent'
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    ai_confidence = db.Column(db.Float)  # confidence score from AI
    method = db.Column(db.String(20)) # 'yolo', 'manual', etc.
    is_manual_override = db.Column(db.Boolean, default=False)
    is_finalized = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    discrepancy_reports = db.relationship('DiscrepancyReport', backref='attendance', lazy=True, cascade="all, delete-orphan")


class ApprovalRequest(db.Model):
    __tablename__ = 'approval_requests'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending/approved/rejected
    note = db.Column(db.Text)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject = db.relationship('Subject', backref=db.backref('approval_requests', cascade="all, delete-orphan"))
    class_ref = db.relationship('Class', backref=db.backref('approval_requests', cascade="all, delete-orphan"))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])


class DiscrepancyReport(db.Model):
    __tablename__ = 'discrepancy_reports'
    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance_records.id'), nullable=False)
    raised_by = db.Column(db.String(120))
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='open')  # open/resolved
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
