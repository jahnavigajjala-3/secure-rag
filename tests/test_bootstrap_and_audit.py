import json
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.bootstrap import ensure_admin_bootstrap
from app.database.database import SessionLocal, init_db
from app.database.models import AuditLog, Role, User
from app.database.seed import DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD, DEV_EMPLOYEE_EMAIL, DEV_EMPLOYEE_PASSWORD, seed_dev_users
from app.main import app

client = TestClient(app)


def test_admin_bootstrap_and_audit_logging():
    init_db()
    seed_dev_users()
    db = SessionLocal()
    try:
        admin_count_before = db.query(User).filter(User.roles.any(Role.name == "admin")).count()
        assert admin_count_before >= 1

        bootstrap_user = ensure_admin_bootstrap(db)
        assert bootstrap_user is None or bootstrap_user.email.lower() == DEV_ADMIN_EMAIL.lower()

        res_login = client.post("/auth/login", json={"email": DEV_ADMIN_EMAIL, "password": DEV_ADMIN_PASSWORD})
        assert res_login.status_code == 200
        token = res_login.json()["access_token"]

        audit_rows = db.query(AuditLog).filter(AuditLog.action == "AUTH_LOGIN_SUCCESS").all()
        assert len(audit_rows) >= 1

        bad_login = client.post("/auth/login", json={"email": DEV_EMPLOYEE_EMAIL, "password": "wrongpass"})
        assert bad_login.status_code == 401
        failed_audit = db.query(AuditLog).filter(AuditLog.action == "AUTH_LOGIN_FAILURE").all()
        assert len(failed_audit) >= 1

        res_protected = client.get("/admin/documents", headers={"Authorization": f"Bearer {token}"})
        assert res_protected.status_code == 200

        res_employee_audit = client.get("/admin/audit-logs", headers={"Authorization": f"Bearer {client.post('/auth/login', json={'email': DEV_EMPLOYEE_EMAIL, 'password': DEV_EMPLOYEE_PASSWORD}).json()['access_token']}"})
        assert res_employee_audit.status_code == 403

        health = client.get("/health")
        assert health.status_code == 200

        ready = client.get("/health/ready")
        assert ready.status_code == 200
    finally:
        db.close()


def test_public_signup_cannot_create_admin():
    init_db()
    seed_dev_users()
    email = f"public_admin_{uuid.uuid4().hex[:6]}@company.com"
    res = client.post(
        "/auth/register",
        json={
            "name": "Nope",
            "email": email,
            "password": "password123",
            "confirm_password": "password123",
            "account_type": "administrator",
            "admin_access_key": "anything"
        },
    )
    assert res.status_code == 201
    user = client.post("/auth/login", json={"email": email, "password": "password123"}).json()["user"]
    assert user["role"] == "employee"
