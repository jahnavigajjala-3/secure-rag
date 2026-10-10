from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User, Role
from app.schemas.rbac import UserCreate, UserResponse, RoleCreate, RoleResponse

router = APIRouter(prefix="/api", tags=["RBAC Management"])


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Create a user without assigning any role.
    """
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with username '{user_in.username}' already exists."
        )

    email = user_in.email or f"{user_in.username}@example.com"
    new_user = User(
        username=user_in.username,
        email=email,
        full_name=user_in.full_name or user_in.username,
        password_hash="placeholder-password-not-used",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/users", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """
    List users and their currently assigned roles.
    """
    users = db.query(User).all()
    return users


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(role_in: RoleCreate, db: Session = Depends(get_db)):
    """
    Create a new role.
    """
    existing_role = db.query(Role).filter(Role.name == role_in.name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role with name '{role_in.name}' already exists."
        )

    new_role = Role(name=role_in.name)
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role


@router.get("/roles", response_model=List[RoleResponse])
def list_roles(db: Session = Depends(get_db)):
    """
    List all existing roles.
    """
    roles = db.query(Role).all()
    return roles


@router.post("/users/{user_id}/roles/{role_id}", response_model=UserResponse)
def assign_role_to_user(user_id: str, role_id: str, db: Session = Depends(get_db)):
    """
    Assign an existing role to an existing user.
    Validates user and role existence and prevents duplicate assignments.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found."
        )

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with id '{role_id}' not found."
        )
    if role in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role.name}' is already assigned to user '{user.username}'."
        )

    user.roles.append(role)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}/roles/{role_id}", response_model=UserResponse)
def remove_role_from_user(user_id: str, role_id: str, db: Session = Depends(get_db)):
    """
    Remove an existing role from an existing user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found."
        )

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with id '{role_id}' not found."
        )

    if role not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role.name}' is not assigned to user '{user.username}'."
        )

    user.roles.remove(role)
    db.commit()
    db.refresh(user)
    return user
