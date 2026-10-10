from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin_user
from app.database.database import get_db
from app.database.models import AuditLog, User

router = APIRouter(prefix="/admin", tags=["Admin Audit Logs"])


@router.get("/audit-logs")
def list_audit_logs(
    actor: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    resource_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if actor:
        query = query.filter(AuditLog.actor_user_id == actor)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if status:
        query = query.filter(AuditLog.status == status)

    total = query.count()
    rows = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    payload = []
    for row in rows:
        payload.append(
            {
                "id": row.id,
                "actor_user_id": row.actor_user_id,
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "status": row.status,
                "metadata": row.metadata,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )

    return {"items": payload, "count": len(payload), "total": total, "limit": limit, "offset": offset}
