import os
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.database.database import get_db
from app.database.models import Role, User
from app.schemas.auth import (
    AdminRegisterRequest,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserAuthResponse,
)
from app.services.audit import create_audit_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

ADMIN_SIGNUP_KEY = os.getenv("ADMIN_SIGNUP_KEY", os.getenv("ADMIN_INVITATION_CODE", "secure_rag_admin_invite_2026"))


def get_user_primary_role(user: User) -> str:
    if not user.roles:
        return "employee"
    role_names = [r.name.lower() for r in user.roles]
    if "admin" in role_names:
        return "admin"
    return role_names[0]


def generate_unique_username(email: str, db: Session) -> str:
    base_username = email.split("@")[0].replace(".", "_").replace("-", "_")
    username = base_username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}_{counter}"
        counter += 1
    return username


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db), http_request: Request = None):
    email_clean = request.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not user.password_hash or not verify_password(request.password, user.password_hash):
        audit = create_audit_service(db)
        audit.record(
            action="AUTH_LOGIN_FAILURE",
            status="FAILURE",
            metadata={"email": email_clean, "reason": "invalid_credentials"},
            ip_address=http_request.client.host if http_request and http_request.client else None,
            user_agent=http_request.headers.get("user-agent") if http_request else None,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email or password you entered is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        audit = create_audit_service(db)
        audit.record(
            action="AUTH_LOGIN_FAILURE",
            status="FAILURE",
            resource_type="user",
            resource_id=user.id,
            metadata={"email": email_clean, "reason": "inactive_user"},
            ip_address=http_request.client.host if http_request and http_request.client else None,
            user_agent=http_request.headers.get("user-agent") if http_request else None,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
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

    audit = create_audit_service(db)
    audit.record(
        action="AUTH_LOGIN_SUCCESS",
        actor_user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        metadata={"role": role_str},
        ip_address=http_request.client.host if http_request and http_request.client else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
    )
    db.commit()

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
def register(request: RegisterRequest, db: Session = Depends(get_db), http_request: Request = None):
    if not request.name or not request.name.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Full name is required.")

    requested_role = str(request.account_type or "employee").strip().lower()
    admin_key = request.admin_access_key
    if requested_role == "admin":
        if not admin_key or admin_key != ADMIN_SIGNUP_KEY:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid administrator access key.")
    else:
        requested_role = "employee"

    email_clean = request.email.strip().lower()
    if "@" not in email_clean or "." not in email_clean:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid email address format.")

    if not request.password or len(request.password) < 6:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 6 characters long.")

    if request.confirm_password is not None and request.password != request.confirm_password:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password confirmation does not match.")

    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    target_role_name = requested_role
    target_role = db.query(Role).filter(Role.name == target_role_name).first()
    if not target_role:
        target_role = Role(name=target_role_name)
        db.add(target_role)
        db.commit()

    username = generate_unique_username(email_clean, db)
    new_user = User(
        name=request.name.strip(),
        full_name=request.name.strip(),
        username=username,
        email=email_clean,
        password_hash=hash_password(request.password),
        is_active=True,
    )
    new_user.roles.append(target_role)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    audit = create_audit_service(db)
    audit.record(
        action="USER_CREATED",
        actor_user_id=new_user.id,
        resource_type="user",
        resource_id=new_user.id,
        metadata={"email": new_user.email, "role": target_role_name},
        ip_address=http_request.client.host if http_request and http_request.client else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
    )
    db.commit()

    return RegisterResponse(
        message="Account created successfully. Please sign in.",
        user=UserAuthResponse(
            id=new_user.id,
            email=new_user.email,
            role=target_role_name,
        ),
    )


@router.post("/register-admin", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_admin(request: AdminRegisterRequest, db: Session = Depends(get_db), http_request: Request = None):
    if request.invitation_code != ADMIN_SIGNUP_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid administrator access key.")

    email_clean = request.email.strip().lower()
    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(name="admin")
        db.add(admin_role)
        db.commit()

    username = generate_unique_username(email_clean, db)
    new_admin = User(
        name=request.name.strip(),
        full_name=request.name.strip(),
        username=username,
        email=email_clean,
        password_hash=hash_password(request.password),
        is_active=True,
    )
    new_admin.roles.append(admin_role)

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    audit = create_audit_service(db)
    audit.record(
        action="USER_CREATED",
        actor_user_id=new_admin.id,
        resource_type="user",
        resource_id=new_admin.id,
        metadata={"email": new_admin.email, "role": "admin"},
        ip_address=http_request.client.host if http_request and http_request.client else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
    )
    db.commit()

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
    return UserAuthResponse(
        id=current_user.id,
        email=current_user.email or f"{current_user.username}@example.com",
        role=get_user_primary_role(current_user),
    )
