import sys
import uuid
from datetime import timedelta
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.database.database import init_db
from app.database.seed import seed_dev_users, DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD, DEV_EMPLOYEE_EMAIL, DEV_EMPLOYEE_PASSWORD
from app.auth.security import create_access_token

client = TestClient(app)


def test_authentication_and_registration_workflow():
    init_db()
    seed_dev_users()

    # 1. Successful Admin Login
    res_admin_login = client.post(
        "/auth/login",
        json={"email": DEV_ADMIN_EMAIL, "password": DEV_ADMIN_PASSWORD}
    )
    assert res_admin_login.status_code == 200
    admin_data = res_admin_login.json()
    assert "access_token" in admin_data
    assert admin_data["token_type"] == "bearer"
    assert admin_data["user"]["email"] == DEV_ADMIN_EMAIL
    assert admin_data["user"]["role"] == "admin"
    admin_token = admin_data["access_token"]
    admin_id = admin_data["user"]["id"]

    # 2. Successful Employee Login
    res_emp_login = client.post(
        "/auth/login",
        json={"email": DEV_EMPLOYEE_EMAIL, "password": DEV_EMPLOYEE_PASSWORD}
    )
    assert res_emp_login.status_code == 200
    emp_data = res_emp_login.json()
    assert emp_data["user"]["email"] == DEV_EMPLOYEE_EMAIL
    assert emp_data["user"]["role"] == "employee"
    emp_token = emp_data["access_token"]

    # 3. Wrong Password Test -> 401
    res_bad_pwd = client.post(
        "/auth/login",
        json={"email": DEV_ADMIN_EMAIL, "password": "wrongpassword123"}
    )
    assert res_bad_pwd.status_code == 401
    assert "incorrect" in res_bad_pwd.json()["detail"].lower()

    # 4. Unknown Email Test -> 401
    res_bad_email = client.post(
        "/auth/login",
        json={"email": "nonexistent@example.com", "password": "anypassword"}
    )
    assert res_bad_email.status_code == 401
    assert "incorrect" in res_bad_email.json()["detail"].lower()

    # 5. Protected GET /auth/me without token -> 401
    res_no_token = client.get("/auth/me")
    assert res_no_token.status_code == 401

    # 6. Protected GET /auth/me with invalid token -> 401
    res_bad_token = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"}
    )
    assert res_bad_token.status_code == 401

    # 7. Protected GET /auth/me with valid Admin token -> 200
    res_valid_me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_valid_me.status_code == 200
    me_data = res_valid_me.json()
    assert me_data["id"] == admin_id
    assert me_data["email"] == DEV_ADMIN_EMAIL
    assert me_data["role"] == "admin"

    # 8. Protected GET /auth/me with expired token -> 401
    expired_token = create_access_token(
        data={"user_id": admin_id, "sub": admin_id, "email": DEV_ADMIN_EMAIL, "role": "admin"},
        expires_delta=timedelta(seconds=-10)
    )
    res_expired = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert res_expired.status_code == 401
    assert "expired" in res_expired.json()["detail"].lower()

    # 9. Public Employee Self-Registration -> 201 Created (Default role = employee)
    new_emp_email = f"user_{uuid.uuid4().hex[:6]}@company.com"
    res_reg = client.post(
        "/auth/register",
        json={
            "name": "Test Employee",
            "email": new_emp_email,
            "password": "password123",
            "confirm_password": "password123"
        }
    )
    assert res_reg.status_code == 201
    reg_data = res_reg.json()
    assert reg_data["user"]["email"] == new_emp_email
    assert reg_data["user"]["role"] == "employee"

    # 10. Login with newly registered employee -> 200 OK
    res_reg_login = client.post(
        "/auth/login",
        json={"email": new_emp_email, "password": "password123"}
    )
    assert res_reg_login.status_code == 200
    assert res_reg_login.json()["user"]["role"] == "employee"

    # 11. Duplicate Email Registration -> 409 Conflict
    res_dup_reg = client.post(
        "/auth/register",
        json={
            "name": "Duplicate User",
            "email": new_emp_email,
            "password": "password123",
            "confirm_password": "password123"
        }
    )
    assert res_dup_reg.status_code == 409
    assert "already exists" in res_dup_reg.json()["detail"].lower()

    # 12. Password Mismatch -> 422
    res_mismatch = client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": f"mismatch_{uuid.uuid4().hex[:4]}@company.com",
            "password": "password123",
            "confirm_password": "different_password"
        }
    )
    assert res_mismatch.status_code == 422

    # 13. Authorized Administrator Registration -> 201 Created (with valid access key)
    admin_signup_email = f"new_admin_{uuid.uuid4().hex[:6]}@company.com"
    res_admin_reg = client.post(
        "/auth/register",
        json={
            "name": "New Admin User",
            "email": admin_signup_email,
            "password": "adminpassword123",
            "confirm_password": "adminpassword123",
            "account_type": "admin",
            "admin_access_key": "secure_rag_admin_invite_2026"
        }
    )
    assert res_admin_reg.status_code == 201
    admin_reg_data = res_admin_reg.json()
    assert admin_reg_data["user"]["email"] == admin_signup_email
    assert admin_reg_data["user"]["role"] == "admin"

    # 14. Login with newly registered Admin -> 200 OK & Role = Admin
    res_new_admin_login = client.post(
        "/auth/login",
        json={"email": admin_signup_email, "password": "adminpassword123"}
    )
    assert res_new_admin_login.status_code == 200
    assert res_new_admin_login.json()["user"]["role"] == "admin"

    # 15. Unauthorized Admin Registration (Invalid Key) -> 403 Forbidden
    res_bad_key = client.post(
        "/auth/register",
        json={
            "name": "Unauthorized Admin",
            "email": f"hacker_{uuid.uuid4().hex[:6]}@company.com",
            "password": "password123",
            "confirm_password": "password123",
            "account_type": "admin",
            "admin_access_key": "wrong_key_123"
        }
    )
    assert res_bad_key.status_code == 403
    assert "invalid administrator access key" in res_bad_key.json()["detail"].lower()

    # 16. Unauthorized Admin Registration (Missing Key) -> 403 Forbidden
    res_missing_key = client.post(
        "/auth/register",
        json={
            "name": "Sneaky Admin",
            "email": f"sneaky_{uuid.uuid4().hex[:6]}@company.com",
            "password": "password123",
            "confirm_password": "password123",
            "account_type": "admin"
        }
    )
    assert res_missing_key.status_code == 403
    assert "invalid administrator access key" in res_missing_key.json()["detail"].lower()

    # 17. Admin Register Endpoint Invitation Code Check -> 403
    res_bad_invite = client.post(
        "/auth/register-admin",
        json={
            "name": "Attacker",
            "email": f"attacker_{uuid.uuid4().hex[:4]}@company.com",
            "password": "password123",
            "invitation_code": "invalid_code_123"
        }
    )
    assert res_bad_invite.status_code == 403

    print("ALL AUTHENTICATION & REGISTRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_authentication_and_registration_workflow()

