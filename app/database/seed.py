import os
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.database.models import User, Role
from app.auth.security import hash_password

DEV_ADMIN_EMAIL = os.getenv("DEV_ADMIN_EMAIL", "admin@example.com")
DEV_ADMIN_PASSWORD = os.getenv("DEV_ADMIN_PASSWORD", "admin123")
DEV_EMPLOYEE_EMAIL = os.getenv("DEV_EMPLOYEE_EMAIL", "employee@example.com")
DEV_EMPLOYEE_PASSWORD = os.getenv("DEV_EMPLOYEE_PASSWORD", "employee123")


def seed_dev_users(db: Session = None) -> None:
    """
    Safely seed local development users admin@example.com and employee@example.com.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # Ensure default roles exist
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin")
            db.add(admin_role)

        employee_role = db.query(Role).filter(Role.name == "employee").first()
        if not employee_role:
            employee_role = Role(name="employee")
            db.add(employee_role)

        db.commit()

        # Seed Admin user
        admin_user = db.query(User).filter(User.email == DEV_ADMIN_EMAIL).first()
        if not admin_user:
            admin_user = User(
                username="admin_user",
                email=DEV_ADMIN_EMAIL,
                password_hash=hash_password(DEV_ADMIN_PASSWORD),
            )
            admin_user.roles.append(admin_role)
            db.add(admin_user)
        elif not admin_user.password_hash:
            admin_user.password_hash = hash_password(DEV_ADMIN_PASSWORD)

        # Seed Employee user
        employee_user = db.query(User).filter(User.email == DEV_EMPLOYEE_EMAIL).first()
        if not employee_user:
            employee_user = User(
                username="employee_user",
                email=DEV_EMPLOYEE_EMAIL,
                password_hash=hash_password(DEV_EMPLOYEE_PASSWORD),
            )
            employee_user.roles.append(employee_role)
            db.add(employee_user)
        elif not employee_user.password_hash:
            employee_user.password_hash = hash_password(DEV_EMPLOYEE_PASSWORD)

        db.commit()
    finally:
        if close_session:
            db.close()
