from flask import Flask
from config import Config
from extensions import db, login_manager
from flask_login import current_user
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Global context: pending approvals badge + today date + permission helper
    @app.context_processor
    def inject_globals():
        from datetime import date
        from utils.auth_utils import user_has_permission
        ctx = {
            'today': str(date.today()),
            'has_permission': lambda perm: user_has_permission(current_user, perm)
        }
        if current_user.is_authenticated and current_user.role in ('admin', 'hod'):
            from models import ApprovalRequest
            ctx['pending_approvals_count'] = ApprovalRequest.query.filter_by(status='pending').count()
        return ctx

    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.teacher import teacher_bp
    from routes.student import student_bp
    from routes.hod import hod_bp
    from routes.director import director_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(hod_bp, url_prefix='/hod')
    app.register_blueprint(director_bp, url_prefix='/director')

    @app.route('/')
    def index():
        from utils.auth_utils import redirect_to_role_dashboard
        from flask import redirect, url_for
        if current_user.is_authenticated:
            return redirect_to_role_dashboard(current_user)
        return redirect(url_for('auth.login'))

    with app.app_context():
        db.create_all()
        seed_demo_data()

    return app

def seed_demo_data():
    from models import User, Department, Class, Subject, Student, Role, Permission, RolePermission
    from utils.auth_utils import DEFAULT_ROLE_PERMISSIONS

    # 1. Seed Roles & Permissions
    for role_name in ['admin', 'director', 'hod', 'teacher', 'student']:
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name, description=f"{role_name.title()} access role")
            db.session.add(role)
    db.session.commit()

    for perm_code in DEFAULT_ROLE_PERMISSIONS['admin']:
        perm = Permission.query.filter_by(code=perm_code).first()
        if not perm:
            perm = Permission(code=perm_code, name=perm_code.replace('_', ' ').title())
            db.session.add(perm)
    db.session.commit()

    if User.query.first():
        # Ensure demo accounts exist even if DB already had users
        seed_missing_demo_accounts()
        return

    # 2. Seed Master Admin
    admin = User(
        username='utkarshyadav29',
        name='Admin User',
        role='admin',
        email='admin@smartattend.edu',
        department='Administration',
        employee_id='ADM001',
        is_active_account=True
    )
    admin.set_password('Rgi@best')
    db.session.add(admin)

    # 3. Seed Demo Department, Class, Subject, Student
    dept = Department(name='Computer Science & Engineering', code='CSE', year=1)
    db.session.add(dept)
    db.session.flush()

    cls = Class(name='First Year CSE', section='A', year=1, department_id=dept.id)
    db.session.add(cls)
    db.session.flush()

    subj = Subject(name='Data Structures & Algorithms', code='CS101', class_id=cls.id, credits=4)
    db.session.add(subj)

    student = Student(student_id='STU101', roll_number='101', name='Alex Morgan', class_id=cls.id, email='alex.morgan@smartattend.edu')
    db.session.add(student)
    db.session.flush()

    student_user = User(
        username='STU101',
        name='Alex Morgan',
        role='student',
        email='alex.morgan@smartattend.edu',
        student_id=student.id,
        is_active_account=True
    )
    student_user.set_password('101')
    db.session.add(student_user)

    # 4. Seed Demo HOD, Director, Teacher
    seed_demo_staff(dept.name)

    db.session.commit()
    print("✅ System initialized securely with unified auth & role-based demo accounts.")

def seed_missing_demo_accounts():
    from models import User, Department
    dept = Department.query.first()
    dept_name = dept.name if dept else 'Computer Science & Engineering'
    seed_demo_staff(dept_name)
    db.session.commit()

def seed_demo_staff(dept_name):
    from models import User

    # HOD
    if not User.query.filter_by(username='HOD001').first():
        hod = User(
            username='HOD001',
            name='Dr. Robert Vance',
            role='hod',
            email='hod.cse@smartattend.edu',
            department=dept_name,
            employee_id='HOD001',
            is_active_account=True
        )
        hod.set_password('hod123')
        db.session.add(hod)

    # Director
    if not User.query.filter_by(username='DIR001').first():
        director = User(
            username='DIR001',
            name='Dr. Eleanor Sterling',
            role='director',
            email='director@smartattend.edu',
            department='Executive Office',
            employee_id='DIR001',
            is_active_account=True
        )
        director.set_password('dir123')
        db.session.add(director)

    # Teacher
    if not User.query.filter_by(username='TCH001').first():
        teacher = User(
            username='TCH001',
            name='Prof. Alan Turing',
            role='teacher',
            email='alan.turing@smartattend.edu',
            department=dept_name,
            employee_id='TCH001',
            is_active_account=True
        )
        teacher.set_password('tch123')
        db.session.add(teacher)

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
