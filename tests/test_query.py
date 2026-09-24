import os
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

client = TestClient(app)

def test_secure_rag_query_generation_and_grounding():
    init_db()
    seed_dev_users()
    db = SessionLocal()

    try:
        # 1. Fetch DB Roles & Users
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        employee_role = db.query(Role).filter(Role.name == "employee").first()

        admin_user = db.query(User).filter(User.email == DEV_ADMIN_EMAIL).first()
        employee_user = db.query(User).filter(User.email == DEV_EMPLOYEE_EMAIL).first()

        # 2. Login Admin & Employee to get JWT tokens
        res_admin_login = client.post("/auth/login", json={"email": DEV_ADMIN_EMAIL, "password": DEV_ADMIN_PASSWORD})
        assert res_admin_login.status_code == 200
        admin_token = res_admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        res_emp_login = client.post("/auth/login", json={"email": DEV_EMPLOYEE_EMAIL, "password": DEV_EMPLOYEE_PASSWORD})
        assert res_emp_login.status_code == 200
        emp_token = res_emp_login.json()["access_token"]
        emp_headers = {"Authorization": f"Bearer {emp_token}"}

        # 3. Create & Ingest Document A: Admin Only
        file_a = Path(tempfile.gettempdir()) / f"q4_financials_{uuid.uuid4().hex[:6]}.txt"
        file_a.write_text("Confidential Q4 Financial Revenue: Company recorded 50 Million USD profit.", encoding="utf-8")
        doc_a = Document(
            filename=file_a.name,
            file_path=str(file_a.resolve()),
            file_size=file_a.stat().st_size,
            status="UPLOADED"
        )
        doc_a.roles.append(admin_role)
        db.add(doc_a)

        # 4. Create & Ingest Document B: Employee Only
        file_b = Path(tempfile.gettempdir()) / f"emp_perks_{uuid.uuid4().hex[:6]}.txt"
        file_b.write_text("Employee Benefits: Free catered lunch is served in the main cafeteria every Friday at 12 PM.", encoding="utf-8")
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

        ingest_document_by_id(doc_a.id, db)
        ingest_document_by_id(doc_b.id, db)

        # -------------------------------------------------------------
        # TEST 1: Unauthenticated Query Request -> 401 Unauthorized
        # -------------------------------------------------------------
        res_unauth = client.post("/api/query", json={"query": "financial revenue"})
        assert res_unauth.status_code == 401
        print("✓ Unauthenticated RAG query blocked (HTTP 401)")

        # -------------------------------------------------------------
        # TEST 2: Admin RAG Query (Has access to both Doc A & B)
        # -------------------------------------------------------------
        query_text = "What is the Q4 financial revenue and employee cafeteria lunch perks?"
        res_admin_query = client.post(
            "/api/query",
            headers=admin_headers,
            json={"query": query_text, "top_k": 5}
        )
        assert res_admin_query.status_code == 200
        admin_data = res_admin_query.json()
        assert admin_data["grounded"] is True
        assert len(admin_data["sources"]) > 0
        
        admin_doc_ids = {s["document_id"] for s in admin_data["sources"]}
        assert doc_a.id in admin_doc_ids, "Admin user MUST have Doc A in source citations"
        print("✓ Admin RAG query returned complete grounded answer with Admin citations")

        # -------------------------------------------------------------
        # TEST 3: Employee RAG Query (Security & Zero Leakage)
        # -------------------------------------------------------------
        res_emp_query = client.post(
            "/api/query",
            headers=emp_headers,
            json={"query": query_text, "top_k": 5}
        )
        assert res_emp_query.status_code == 200
        emp_data = res_emp_query.json()
        emp_doc_ids = {s["document_id"] for s in emp_data["sources"]}
        
        # CRITICAL RBAC SECURITY ASSERTION
        assert doc_a.id not in emp_doc_ids, "SECURITY VIOLATION: Employee received Admin-only document citation!"
        assert doc_b.id in emp_doc_ids, "Employee MUST receive authorized Document B citation"
        
        # Verify answer content does not leak financial secret
        assert "50 Million" not in emp_data["answer"], "SECURITY VIOLATION: Financial secret leaked to employee in LLM text!"
        print("✓ Employee RAG query strictly bounded (Zero Leakage in sources & answer text)")

        # -------------------------------------------------------------
        # TEST 4: Employee Query for Admin-Only Secret (Empty Context Fallback)
        # -------------------------------------------------------------
        secret_query = "What was the exact Q4 financial revenue?"
        res_emp_secret = client.post(
            "/api/query",
            headers=emp_headers,
            json={"query": secret_query, "top_k": 5}
        )
        assert res_emp_secret.status_code == 200
        emp_secret_data = res_emp_secret.json()
        
        assert emp_secret_data["grounded"] is False
        assert len(emp_secret_data["sources"]) == 0
        assert emp_secret_data["retrieved_chunk_count"] == 0
        assert "cannot answer" in emp_secret_data["answer"].lower() or "not found" in emp_secret_data["answer"].lower()
        print("✓ Empty context short-circuit fallback correctly executed for unauthorized query")

        # Cleanup temp files
        file_a.unlink(missing_ok=True)
        file_b.unlink(missing_ok=True)

        print("\n==================================================")
        print("ALL MILESTONE 5 SECURE RAG QUERY & GROUNDING TESTS PASSED!")
        print("==================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    test_secure_rag_query_generation_and_grounding()
