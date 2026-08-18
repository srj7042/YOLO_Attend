from functools import wraps
from flask import request, redirect, url_for, flash
from flask_login import current_user
from urllib.parse import urlparse, urljoin
from extensions import db
from models import User, Student, Role, Permission, RolePermission, UserPermission, AuditLog

DEFAULT_ROLE_PERMISSIONS = {
    'admin': {
        'view_dashboard', 'view_students', 'add_student', 'edit_student', 'delete_student',
        'view_attendance', 'mark_attendance', 'edit_attendance', 'approve_attendance',
        'view_reports', 'generate_reports', 'manage_subjects', 'manage_classes',
        'manage_teachers', 'manage_students', 'manage_users', 'manage_roles',
        'manage_permissions', 'view_analytics', 'manage_system_settings',
        'view_audit_logs', 'approve_teacher', 'approve_student', 'view_teachers',
        'view_hods', 'view_departments', 'view_profile', 'view_timetable'
    },
    'director': {
        'view_dashboard', 'view_students', 'view_teachers', 'view_hods', 'view_departments',
        'view_attendance', 'view_reports', 'generate_reports', 'view_analytics',
        'view_audit_logs'
    },
    'hod': {
        'view_dashboard', 'view_students', 'view_teachers', 'view_classes', 'view_subjects',
        'view_attendance', 'approve_attendance', 'view_reports', 'generate_reports',
        'approve_teacher', 'approve_student', 'view_analytics'
    },
    'teacher': {
        'view_dashboard', 'view_students', 'view_attendance', 'mark_attendance',
        'edit_attendance', 'view_reports'
    },
    'student': {
        'view_dashboard', 'view_attendance', 'view_reports', 'view_subjects',
        'view_timetable', 'view_profile'
    }
}

def find_user_by_identifier(identifier):
    """
    Intelligently search for a matching user account given any identifier string:
    Username, Employee ID, User Email, Student ID / Reg Number / Roll Number.
    Performs normalized matching.
    """
    if not identifier:
        return None

    clean_id = identifier.strip()
    if not clean_id:
        return None

    # 1. Search directly in User model (case-insensitive for username, employee_id, email)
    user = User.query.filter(
        (db.func.lower(User.username) == clean_id.lower()) |
        (db.func.lower(User.employee_id) == clean_id.lower()) |
        (db.func.lower(User.email) == clean_id.lower())
    ).first()

    if user:
        return user

    # 2. Search in Student table by registration_number, student_id, roll_number, email
    student = Student.query.filter(
        (db.func.lower(Student.student_id) == clean_id.lower()) |
        (db.func.lower(Student.registration_number) == clean_id.lower()) |
        (db.func.lower(Student.roll_number) == clean_id.lower()) |
        (db.func.lower(Student.email) == clean_id.lower())
    ).first()

    if student:
        # Search for User account linked via student_id foreign key or matching username
        user = User.query.filter_by(student_id=student.id).first()
        if not user:
            user = User.query.filter(
                (db.func.lower(User.username) == student.student_id.lower()) |
                (db.func.lower(User.username) == (student.registration_number or '').lower())
            ).first()
        if user:
            return user

    return None

def get_user_permissions(user):
    """
    Returns set of permission codes available to the user based on role and custom permissions.
    """
    if not user or not user.is_authenticated:
        return set()

    role = (user.role or '').lower()
    perms = set(DEFAULT_ROLE_PERMISSIONS.get(role, set()))

    # DB Role permissions override if present
    db_role = Role.query.filter(db.func.lower(Role.name) == role).first()
    if db_role and db_role.role_permissions:
        perms = set()
        for rp in db_role.role_permissions:
            if rp.permission:
                perms.add(rp.permission.code)

    # Custom User-level Permission overrides
    if user.custom_permissions:
        for up in user.custom_permissions:
            if up.permission:
                if up.is_granted:
                    perms.add(up.permission.code)
                else:
                    perms.discard(up.permission.code)

    return perms

def user_has_permission(user, permission_code):
    """
    Checks if a user has a given permission.
    Admins automatically have all permissions.
    """
    if not user or not user.is_authenticated:
        return False
    if user.role == 'admin':
        return True
    perms = get_user_permissions(user)
    return permission_code in perms

def role_required(*roles):
    """
    Decorator to restrict route access to specific role(s).
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login', next=request.url))
            if current_user.role not in roles and current_user.role != 'admin':
                flash("You don't have permission to access this page.", 'error')
                return redirect_to_role_dashboard(current_user)
            return f(*args, **kwargs)
        return decorated
    return decorator

def permission_required(permission_code):
    """
    Decorator to restrict route access by granular permission code.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login', next=request.url))
            if not user_has_permission(current_user, permission_code):
                flash("You don't have permission to access this page.", 'error')
                return redirect_to_role_dashboard(current_user)
            return f(*args, **kwargs)
        return decorated
    return decorator

def redirect_to_role_dashboard(user):
    """
    Redirects user to their appropriate role-based dashboard.
    """
    if not user or not user.is_authenticated:
        return redirect(url_for('auth.login'))
    role = (user.role or '').lower()
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'director':
        return redirect(url_for('director.dashboard'))
    elif role == 'hod':
        return redirect(url_for('hod.dashboard'))
    elif role == 'student':
        return redirect(url_for('student.dashboard'))
    elif role == 'teacher':
        return redirect(url_for('teacher.dashboard'))
    return redirect(url_for('auth.login'))

def log_audit_event(action, description=None, user_id=None, username=None):
    """
    Records an audit log entry for security and access monitoring.
    """
    try:
        uid = user_id or (current_user.id if current_user.is_authenticated else None)
        uname = username or (current_user.username if current_user.is_authenticated else 'Anonymous')
        ip = request.remote_addr if request else None

        log = AuditLog(
            user_id=uid,
            username=uname,
            action=action,
            ip_address=ip,
            description=description
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ Failed to record audit log: {e}")

def is_safe_url(target):
    """
    Validates target URL to prevent Open Redirect vulnerabilities.
    """
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc
