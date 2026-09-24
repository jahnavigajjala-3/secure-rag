import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User, Role
from app.auth.security import verify_password, hash_password, create_access_token
from app.auth.dependencies import get_current_user
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    AdminRegisterRequest,
    TokenResponse,
    UserAuthResponse,
    RegisterResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

ADMIN_SIGNUP_KEY = os.getenv("ADMIN_SIGNUP_KEY", os.getenv("ADMIN_INVITATION_CODE", "secure_rag_admin_invite_2026"))
ADMIN_INVITATION_CODE = ADMIN_SIGNUP_KEY


def get_user_primary_role(user: User) -> str:
    """
    Helper to extract primary role string compatible with RBAC setup.
    """
    if not user.roles:
        return "employee"
    role_names = [r.name.lower() for r in user.roles]
    if "admin" in role_names:
        return "admin"
    return role_names[0]


def generate_unique_username(email: str, db: Session) -> str:
    """
    Generate a unique username from email prefix.
    """
    base_username = email.split("@")[0].replace(".", "_").replace("-", "_")
    username = base_username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}_{counter}"
        counter += 1
    return username


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user with email and password, returning JWT access token.
    """
    email_clean = request.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not user.password_hash or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email or password you entered is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role_str = get_user_primary_role(user)
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "sub": user.id,
            "email": user.email,
            "role": role_str,
        }
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserAuthResponse(
            id=user.id,
            email=user.email or "",
            role=role_str,
        ),
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Unified account registration endpoint supporting Employee and Administrator creation.
    Administrator account creation requires server-side validation of admin_access_key against ADMIN_SIGNUP_KEY.
    """
    # 1. Input Validation
    if not request.name or not request.name.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Full name is required.")

    email_clean = request.email.strip().lower()
    if "@" not in email_clean or "." not in email_clean:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid email address format.")

    if not request.password or len(request.password) < 6:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 6 characters long.")

    if request.confirm_password is not None and request.password != request.confirm_password:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password confirmation does not match.")

    # 2. Check Email Uniqueness
    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    # 3. Determine Requested Role & Validate Admin Key Server-side
    account_type_clean = (request.account_type or "employee").strip().lower()
    if account_type_clean in ["admin", "administrator"]:
        if not request.admin_access_key or request.admin_access_key != ADMIN_SIGNUP_KEY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid administrator access key."
            )
        target_role_name = "admin"
        success_msg = "Administrator account created successfully. Please sign in."
    else:
        target_role_name = "employee"
        success_msg = "Account created successfully. Please sign in."

    # 4. Role Retrieval/Creation
    target_role = db.query(Role).filter(Role.name == target_role_name).first()
    if not target_role:
        target_role = Role(name=target_role_name)
        db.add(target_role)
        db.commit()

    # 5. Create User Record
    username = generate_unique_username(email_clean, db)
    new_user = User(
        name=request.name.strip(),
        username=username,
        email=email_clean,
        password_hash=hash_password(request.password),
    )
    new_user.roles.append(target_role)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return RegisterResponse(
        message=success_msg,
        user=UserAuthResponse(
            id=new_user.id,
            email=new_user.email,
            role=target_role_name,
        ),
    )


@router.post("/register-admin", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_admin(request: AdminRegisterRequest, db: Session = Depends(get_db)):
    """
    Protected invitation-based administrator account creation endpoint.
    Validates backend invitation code before granting the 'admin' role.
    """
    if request.invitation_code != ADMIN_SIGNUP_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid administrator access key."
        )

    email_clean = request.email.strip().lower()
    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(name="admin")
        db.add(admin_role)
        db.commit()

    username = generate_unique_username(email_clean, db)
    new_admin = User(
        name=request.name.strip(),
        username=username,
        email=email_clean,
        password_hash=hash_password(request.password),
    )
    new_admin.roles.append(admin_role)

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return RegisterResponse(
        message="Administrator account created successfully. Please sign in.",
        user=UserAuthResponse(
            id=new_admin.id,
            email=new_admin.email,
            role="admin",
        ),
    )


@router.get("/me", response_model=UserAuthResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Return currently authenticated user identity and role.
    """
    return UserAuthResponse(
        id=current_user.id,
        email=current_user.email or f"{current_user.username}@example.com",
        role=get_user_primary_role(current_user),
    )
