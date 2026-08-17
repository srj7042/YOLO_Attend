from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student.dashboard'))
        return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'teacher')

        # Find user account
        user = User.query.filter_by(username=username).first()
        
        # If student login, fallback search by student_id or roll_number if username match fails
        if not user and role == 'student':
            from models import Student
            st = Student.query.filter((Student.student_id == username) | (Student.roll_number == username)).first()
            if st:
                user = User.query.filter_by(student_id=st.id, role='student').first()

        if user and user.check_password(password) and user.role == role:
            login_user(user, remember=request.form.get('remember') == 'on')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role == 'student':
                return redirect(url_for('student.dashboard'))
            return redirect(url_for('teacher.dashboard'))
            
        flash('Invalid credentials. Please check your username/roll number, password, and role.', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('teacher.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose another.', 'error')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email is already registered. Please login.', 'error')
            return redirect(url_for('auth.register'))

        # Create new Teacher user (inactive until approved)
        new_teacher = User(
            name=name,
            username=username,
            email=email,
            role='teacher',
            employee_id=f"TCH{User.query.filter_by(role='teacher').count() + 1:03d}",
            department='Pending',
            is_active_account=False
        )
        new_teacher.set_password(password)
        
        from extensions import db
        db.session.add(new_teacher)
        db.session.commit()
        
        flash('Registration successful! Please wait for admin approval before logging in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip() # Registration Number or Username
        email = request.form.get('email', '').strip().lower()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not identifier or not email or not new_password:
            flash('All fields are required.', 'error')
            return render_template('auth/forgot_password.html')

        if new_password != confirm_password:
            flash('Passwords do not match. Please re-enter.', 'error')
            return render_template('auth/forgot_password.html')

        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('auth/forgot_password.html')

        # Find user account
        user = User.query.filter((User.username == identifier) & (User.role == 'student')).first()
        
        if not user:
            from models import Student
            st = Student.query.filter((Student.registration_number == identifier) | (Student.student_id == identifier) | (Student.roll_number == identifier)).first()
            if st:
                user = User.query.filter_by(student_id=st.id, role='student').first()

        if user and user.email and user.email.lower() == email:
            user.set_password(new_password)
            from extensions import db
            db.session.commit()
            flash('✅ Password updated successfully! Please log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('No matching verified student account found with the provided Registration Number and Email.', 'error')

    return render_template('auth/forgot_password.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
