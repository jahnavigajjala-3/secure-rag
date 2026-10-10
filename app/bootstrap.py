import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.config import settings
from app.database.models import Role, User

logger = logging.getLogger(__name__)


def ensure_admin_bootstrap(db: Session) -> Optional[User]:
    """Create a single bootstrap admin if configured and no admin exists yet."""
    if not settings.ADMIN_BOOTSTRAP_EMAIL or not settings.ADMIN_BOOTSTRAP_PASSWORD:
        return None

    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(name="admin")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)

    existing_admin = db.query(User).filter(User.email == settings.ADMIN_BOOTSTRAP_EMAIL.lower()).first()
    if existing_admin:
        return existing_admin

    if db.query(User).filter(User.roles.any(Role.name == "admin")).count() > 0:
        return None

    admin_user = User(
        username="bootstrap_admin",
        email=settings.ADMIN_BOOTSTRAP_EMAIL.lower(),
        password_hash=hash_password(settings.ADMIN_BOOTSTRAP_PASSWORD),
        name="Bootstrap Administrator",
        full_name="Bootstrap Administrator",
        is_active=True,
    )
    admin_user.roles.append(admin_role)
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    logger.info("Bootstrap admin created successfully.")
    return admin_user
