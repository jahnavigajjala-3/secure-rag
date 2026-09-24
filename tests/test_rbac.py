import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.database.database import init_db

client = TestClient(app)


def test_rbac_user_role_workflow():
    init_db()
    
    # 1. Create a user without assigning any role
    username = f"alice_admin_{uuid.uuid4().hex[:6]}"
    res_user = client.post("/api/users", json={"username": username})
    assert res_user.status_code == 201
    user_data = res_user.json()
    assert user_data["username"] == username
    assert user_data["roles"] == []
    user_id = user_data["id"]

    # 2. Create roles
    role1_name = f"role1_{uuid.uuid4().hex[:6]}"
    res_role1 = client.post("/api/roles", json={"name": role1_name})
    assert res_role1.status_code == 201
    role1_data = res_role1.json()
    assert role1_data["name"] == role1_name
    role1_id = role1_data["id"]

    role2_name = f"role2_{uuid.uuid4().hex[:6]}"
    res_role2 = client.post("/api/roles", json={"name": role2_name})
    assert res_role2.status_code == 201
    role2_id = res_role2.json()["id"]

    # 3. List roles
    res_list_roles = client.get("/api/roles")
    assert res_list_roles.status_code == 200
    roles_list = res_list_roles.json()
    role_names = [r["name"] for r in roles_list]
    assert role1_name in role_names
    assert role2_name in role_names

    # 4. List users
    res_list_users = client.get("/api/users")
    assert res_list_users.status_code == 200
    users_list = res_list_users.json()
    target_user = next((u for u in users_list if u["id"] == user_id), None)
    assert target_user is not None
    assert len(target_user["roles"]) == 0

    # 5. Assign existing role to existing user
    res_assign = client.post(f"/api/users/{user_id}/roles/{role1_id}")
    assert res_assign.status_code == 200
    assigned_data = res_assign.json()
    assert len(assigned_data["roles"]) == 1
    assert assigned_data["roles"][0]["id"] == role1_id

    # 6. Prevent duplicate role assignment
    res_dup = client.post(f"/api/users/{user_id}/roles/{role1_id}")
    assert res_dup.status_code == 400
    assert "already assigned" in res_dup.json()["detail"].lower()

    # 7. Validate non-existent user / role error
    res_bad_user = client.post(f"/api/users/non-existent-user-id/roles/{role1_id}")
    assert res_bad_user.status_code == 404
    assert "user" in res_bad_user.json()["detail"].lower()

    res_bad_role = client.post(f"/api/users/{user_id}/roles/non-existent-role-id")
    assert res_bad_role.status_code == 404
    assert "role" in res_bad_role.json()["detail"].lower()

    # 8. Assign a second role to user
    res_assign2 = client.post(f"/api/users/{user_id}/roles/{role2_id}")
    assert res_assign2.status_code == 200
    assigned_data2 = res_assign2.json()
    assert len(assigned_data2["roles"]) == 2

    # 9. Remove role from user
    res_remove = client.delete(f"/api/users/{user_id}/roles/{role1_id}")
    assert res_remove.status_code == 200
    removed_data = res_remove.json()
    remaining_role_ids = [r["id"] for r in removed_data["roles"]]
    assert role1_id not in remaining_role_ids
    assert role2_id in remaining_role_ids

    print("ALL RBAC TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_rbac_user_role_workflow()
