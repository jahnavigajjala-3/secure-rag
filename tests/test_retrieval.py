import io
import sys
import tempfile
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.database.database import init_db, SessionLocal
from app.database.seed import seed_dev_users, DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD, DEV_EMPLOYEE_EMAIL, DEV_EMPLOYEE_PASSWORD
from app.database.models import User, Role, Document
from app.auth.security import hash_password
from app.ingestion.pipeline import ingest_document_by_id
from app.retrieval.retriever import retrieve_for_user

client = TestClient(app)

def test_authorized_retrieval_security_enforcement():
    init_db()
    seed_dev_users()
    db = SessionLocal()

    try:
        # 1. Fetch DB Roles
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        employee_role = db.query(Role).filter(Role.name == "employee").first()

        # 2. Create Unassigned User with NO roles
        unassigned_username = f"guest_{uuid.uuid4().hex[:6]}"
        unassigned_user = User(
            username=unassigned_username,
            email=f"{unassigned_username}@example.com",
            password_hash=hash_password("password123")
        )
        db.add(unassigned_user)
        db.commit()

        # Fetch Admin and Employee user records
        admin_user = db.query(User).filter(User.email == DEV_ADMIN_EMAIL).first()
        employee_user = db.query(User).filter(User.email == DEV_EMPLOYEE_EMAIL).first()

        # 3. Create Document A: Admin Only (Confidential Secret)
        file_a = Path(tempfile.gettempdir()) / f"admin_secret_{uuid.uuid4().hex[:6]}.txt"
        file_a.write_text("Confidential Security Code: Alpha-Omega-999-Secret-Vault-Access.", encoding="utf-8")
        doc_a = Document(
            filename=file_a.name,
            file_path=str(file_a.resolve()),
            file_size=file_a.stat().st_size,
            status="UPLOADED"
        )
        doc_a.roles.append(admin_role)
        db.add(doc_a)

        # 4. Create Document B: Employee Only (Handbook)
        file_b = Path(tempfile.gettempdir()) / f"emp_handbook_{uuid.uuid4().hex[:6]}.txt"
        file_b.write_text("Employee Policy Guide: All employees get 20 days paid leave annually.", encoding="utf-8")
        doc_b = Document(
            filename=file_b.name,
            file_path=str(file_b.resolve()),
            file_size=file_b.stat().st_size,
            status="UPLOADED"
        )
        doc_b.roles.append(employee_role)
        db.add(doc_b)

        db.commit()
        db.refresh(doc_a)
        db.refresh(doc_b)

        # 5. Ingest Documents into Vector Store
        ingest_document_by_id(doc_a.id, db)
        ingest_document_by_id(doc_b.id, db)

        # -------------------------------------------------------------
        # VERIFICATION 1: Admin User Retrieval (Has access to Doc A & B)
        # -------------------------------------------------------------
        query = "What is the secret security code and employee leave policy?"
        admin_chunks = retrieve_for_user(query=query, user=admin_user, db=db, top_k=5)
        admin_doc_ids = {c["metadata"]["document_id"] for c in admin_chunks}
        assert doc_a.id in admin_doc_ids, "Admin user MUST be able to retrieve Admin-only Document A."
        print("✓ Admin user successfully retrieved Admin-restricted chunks")

        # -------------------------------------------------------------
        # VERIFICATION 2: Employee User Retrieval (Has access ONLY to Doc B)
        # -------------------------------------------------------------
        emp_chunks = retrieve_for_user(query=query, user=employee_user, db=db, top_k=5)
        emp_doc_ids = {c["metadata"]["document_id"] for c in emp_chunks}
        
        # SECURITY CRITICAL ASSERTION: Zero Leakage of Admin Document A to Employee User
        assert doc_a.id not in emp_doc_ids, "SECURITY ERROR: Employee user retrieved Admin-only document chunk!"
        assert doc_b.id in emp_doc_ids, "Employee user MUST retrieve authorized Document B chunk."
        
        # Verify text content does not contain secret code
        for chunk in emp_chunks:
            assert "Alpha-Omega-999" not in chunk["text"], "SECURITY FAILURE: Secret content leaked to employee!"
        print("✓ Employee user retrieval strictly bounded (Zero Leakage of Admin secret)")

        # -------------------------------------------------------------
        # VERIFICATION 3: Unassigned User Retrieval (No roles -> 0 chunks)
        # -------------------------------------------------------------
        unassigned_chunks = retrieve_for_user(query=query, user=unassigned_user, db=db, top_k=5)
        assert len(unassigned_chunks) == 0, "User with no assigned roles MUST retrieve 0 chunks."
        print("✓ Unassigned user retrieval blocked pre-search (0 chunks returned)")

        # -------------------------------------------------------------
        # VERIFICATION 4: API Endpoint (POST /api/retrieval/search)
        # -------------------------------------------------------------
        # 4a. Login Admin
        res_login_admin = client.post("/auth/login", json={"email": DEV_ADMIN_EMAIL, "password": DEV_ADMIN_PASSWORD})
        admin_token = res_login_admin.json()["access_token"]
        
        # 4b. Login Employee
        res_login_emp = client.post("/auth/login", json={"email": DEV_EMPLOYEE_EMAIL, "password": DEV_EMPLOYEE_PASSWORD})
        emp_token = res_login_emp.json()["access_token"]

        # 4c. Unauthenticated search attempt -> 401 Unauthorized
        res_unauth = client.post("/api/retrieval/search", json={"query": "security code"})
        assert res_unauth.status_code == 401, "Unauthenticated retrieval must return 401"

        # 4d. Employee Search via API -> Chunks strictly filtered
        res_emp_api = client.post(
            "/api/retrieval/search",
            headers={"Authorization": f"Bearer {emp_token}"},
            json={"query": "secret security code leave policy"}
        )
        assert res_emp_api.status_code == 200
        emp_api_chunks = res_emp_api.json()["retrieved_chunks"]
        for c in emp_api_chunks:
            assert c["metadata"]["document_id"] != doc_a.id, "API Leakage: Admin doc returned to Employee"

        print("✓ API Endpoint POST /api/retrieval/search verified with full RBAC enforcement")

        # Cleanup temp files
        file_a.unlink(missing_ok=True)
        file_b.unlink(missing_ok=True)

        print("\n==================================================")
        print("ALL MILESTONE 4 AUTHORIZED RETRIEVAL TESTS PASSED!")
        print("==================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    test_authorized_retrieval_security_enforcement()
