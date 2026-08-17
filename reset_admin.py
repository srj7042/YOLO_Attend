"""Full DB reset — wipes ALL data, keeps only master admin."""
from app import create_app
from extensions import db
from models import User, Department, Class, Subject, Student, AttendanceRecord, ApprovalRequest

app = create_app()
with app.app_context():
    # Wipe everything in dependency order
    AttendanceRecord.query.delete()
    ApprovalRequest.query.delete()
    Student.query.delete()
    Subject.query.delete()
    Class.query.delete()
    Department.query.delete()
    User.query.delete()
    db.session.commit()

    # Recreate master admin only
    admin = User(
        username='utkarshyadav29',
        name='Admin',
        role='admin',
        email='admin@smartattend.edu',
        department='Administration',
        employee_id='ADM001',
        is_active_account=True
    )
    admin.set_password('Rgi@best')
    db.session.add(admin)
    db.session.commit()

    u = User.query.filter_by(username='utkarshyadav29').first()
    print(f"[OK] DB wiped. Admin ready: {u.username} | pw_ok={u.check_password('Rgi@best')}")
    print(f"     Students: {Student.query.count()}, Departments: {Department.query.count()}, Users: {User.query.count()}")
