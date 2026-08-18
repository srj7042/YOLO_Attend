from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from utils.auth_utils import find_user_by_identifier, redirect_to_role_dashboard, log_audit_event, is_safe_url
from extensions import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect_to_role_dashboard(current_user)

    if request.method == 'POST':
        identifier = request.form.get('identifier', request.form.get('username', '')).strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') in ('on', 'true', '1', True)

        if not identifier or not password:
            flash('Please enter both ID/Username and password.', 'error')
            return render_template('auth/login.html')

        user = find_user_by_identifier(identifier)

        if not user or not user.check_password(password):
            log_audit_event('login_failed', description=f"Failed login attempt for identifier: {identifier}")
            flash('Invalid ID or password.', 'error')
            return render_template('auth/login.html')

        if not user.is_active_account:
            log_audit_event('login_failed', user_id=user.id, username=user.username, description="Inactive account login attempt")
            flash('Your account is currently inactive. Please contact the administrator.', 'error')
            return render_template('auth/login.html')

        # Authentication successful
        login_user(user, remember=remember)
        log_audit_event('login_success', user_id=user.id, username=user.username, description=f"Logged in successfully as {user.role}")

        next_page = request.args.get('next')
        if next_page and is_safe_url(next_page):
            return redirect(next_page)

        return redirect_to_role_dashboard(user)

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect_to_role_dashboard(current_user)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if User.query.filter(db.func.lower(User.username) == username.lower()).first():
            flash('Username is already taken. Please choose another.', 'error')
            return redirect(url_for('auth.register'))

        if User.query.filter(db.func.lower(User.email) == email.lower()).first():
            flash('Email is already registered. Please login.', 'error')
            return redirect(url_for('auth.register'))

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

        db.session.add(new_teacher)
        db.session.commit()

        log_audit_event('user_registered', user_id=new_teacher.id, username=new_teacher.username, description="New teacher registration pending approval")
        flash('Registration successful! Please wait for administrator approval before logging in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
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

        user = find_user_by_identifier(identifier)

        if user and user.email and user.email.lower() == email:
            user.set_password(new_password)
            db.session.commit()
            log_audit_event('password_change', user_id=user.id, username=user.username, description="Password reset via forgot-password route")
            flash('✅ Password updated successfully! Please log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Password reset failed. Please verify your ID/Username and registered Email.', 'error')

    return render_template('auth/forgot_password.html')

@auth_bp.route('/logout')
@login_required
def logout():
    log_audit_event('logout', description="User logged out")
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
