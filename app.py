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

    # Global context: pending approvals badge + today date
    @app.context_processor
    def inject_globals():
        from datetime import date
        ctx = {'today': str(date.today())}
        if current_user.is_authenticated and current_user.role == 'admin':
            from models import ApprovalRequest
            ctx['pending_approvals_count'] = ApprovalRequest.query.filter_by(status='pending').count()
        return ctx

    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.teacher import teacher_bp
    from routes.student import student_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(student_bp, url_prefix='/student')

    @app.route('/')
    def index():
        from flask import redirect, url_for
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif current_user.role == 'student':
                return redirect(url_for('student.dashboard'))
            return redirect(url_for('teacher.dashboard'))
        return redirect(url_for('auth.login'))

    with app.app_context():
        db.create_all()
        seed_demo_data()

    return app

def seed_demo_data():
    from models import User
    
    if User.query.first():
        return

    # Seed the strict master admin account
    admin = User(username='utkarshyadav29', name='Admin User', role='admin',
                 email='admin@smartattend.edu', department='Administration', employee_id='ADM001', is_active_account=True)
    admin.set_password('Rgi@best')
    
    from extensions import db
    db.session.add(admin)

    # Seed demo department, class, student, and student login
    from models import Department, Class, Subject, Student
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

    student_user = User(username='STU101', name='Alex Morgan', role='student', email='alex.morgan@smartattend.edu', student_id=student.id, is_active_account=True)
    student_user.set_password('101')
    db.session.add(student_user)

    db.session.commit()
    print("✅ System initialized securely with master admin and demo student (Username: STU101 / Pass: 101).")

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
