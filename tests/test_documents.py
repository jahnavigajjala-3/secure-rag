import io
import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.database.database import init_db
from app.database.seed import seed_dev_users, DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD, DEV_EMPLOYEE_EMAIL, DEV_EMPLOYEE_PASSWORD

client = TestClient(app)


def test_document_management_workflow():
    init_db()
    seed_dev_users()

    # 1. Login Admin & Employee
    admin_login = client.post("/auth/login", json={"email": DEV_ADMIN_EMAIL, "password": DEV_ADMIN_PASSWORD})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    emp_login = client.post("/auth/login", json={"email": DEV_EMPLOYEE_EMAIL, "password": DEV_EMPLOYEE_PASSWORD})
    assert emp_login.status_code == 200
    emp_token = emp_login.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # 2. Unauthenticated Upload Attempt -> 401 Unauthorized
    dummy_file = ("unauth_doc.pdf", io.BytesIO(b"%PDF-1.4 sample content"), "application/pdf")
    res_unauth = client.post("/admin/documents", files={"file": dummy_file})
    assert res_unauth.status_code == 401

    # 3. Employee Upload Attempt -> 403 Forbidden
    emp_file = ("emp_doc.pdf", io.BytesIO(b"%PDF-1.4 employee test content"), "application/pdf")
    res_emp_upload = client.post(
        "/admin/documents",
        headers=emp_headers,
        files={"file": emp_file}
    )
    assert res_emp_upload.status_code == 403
    assert "admin privilege required" in res_emp_upload.json()["detail"].lower()

    # 4. Admin Upload with Allowed Roles -> 201 Created
    filename = f"q3_audit_{uuid.uuid4().hex[:6]}.pdf"
    audit_file = (filename, io.BytesIO(b"%PDF-1.4 Q3 Financial Audit Report content."), "application/pdf")
    res_admin_upload = client.post(
        "/admin/documents",
        headers=admin_headers,
        files={"file": audit_file},
        data={"allowed_roles": ["admin", "employee"]}
    )
    assert res_admin_upload.status_code == 201
    doc_data = res_admin_upload.json()
    assert doc_data["filename"] == filename
    assert "admin" in [r.lower() for r in doc_data["accessible_roles"]]
    assert "employee" in [r.lower() for r in doc_data["accessible_roles"]]
    doc_id = doc_data["id"]

    # 5. Admin Document List (`GET /admin/documents`) -> 200 OK
    res_admin_list = client.get("/admin/documents", headers=admin_headers)
    assert res_admin_list.status_code == 200
    admin_docs = res_admin_list.json()
    assert any(d["id"] == doc_id for d in admin_docs)

    # 6. Employee Admin List Attempt (`GET /admin/documents`) -> 403 Forbidden
    res_emp_list_admin = client.get("/admin/documents", headers=emp_headers)
    assert res_emp_list_admin.status_code == 403

    # 7. Create Custom Role to test role validation
    role_name = f"analyst_{uuid.uuid4().hex[:6]}"
    res_role = client.post("/api/roles", json={"name": role_name})
    assert res_role.status_code == 201

    # 8. Update Access Policy (`PUT /admin/documents/{id}/access`) with valid roles -> 200 OK
    res_update_access = client.put(
        f"/admin/documents/{doc_id}/access",
        headers=admin_headers,
        json={"allowed_roles": ["admin", role_name]}
    )
    assert res_update_access.status_code == 200
    updated_doc = res_update_access.json()
    assert role_name in updated_doc["accessible_roles"]
    assert "employee" not in [r.lower() for r in updated_doc["accessible_roles"]]

    # 9. Employee Access Policy Update Attempt -> 403 Forbidden
    res_emp_update_access = client.put(
        f"/admin/documents/{doc_id}/access",
        headers=emp_headers,
        json={"allowed_roles": ["admin"]}
    )
    assert res_emp_update_access.status_code == 403

    # 10. Update Access Policy with Invalid Role -> 400 Bad Request
    res_bad_role = client.put(
        f"/admin/documents/{doc_id}/access",
        headers=admin_headers,
        json={"allowed_roles": ["invalid_nonexistent_role"]}
    )
    assert res_bad_role.status_code == 400
    assert "invalid or does not exist" in res_bad_role.json()["detail"].lower()

    # 11. Missing Document Access Policy Update -> 404 Not Found
    res_missing_doc = client.put(
        f"/admin/documents/{uuid.uuid4()}/access",
        headers=admin_headers,
        json={"allowed_roles": ["admin"]}
    )
    assert res_missing_doc.status_code == 404

    # 12. Delete Document (`DELETE /admin/documents/{id}`) -> 200 OK
    res_delete = client.delete(f"/admin/documents/{doc_id}", headers=admin_headers)
    assert res_delete.status_code == 200
    assert res_delete.json()["id"] == doc_id

    # Verify document is removed from list
    res_list_after = client.get("/admin/documents", headers=admin_headers)
    assert not any(d["id"] == doc_id for d in res_list_after.json())

    print("ALL MILESTONE 2 DOCUMENT MANAGEMENT & ACCESS CONTROL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_document_management_workflow()
