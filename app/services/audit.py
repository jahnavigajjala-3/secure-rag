import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.database.models import AuditLog, User


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        action: str,
        actor_user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        safe_metadata = self._sanitize_metadata(metadata or {})
        record = AuditLog(
            id=str(uuid.uuid4()),
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            audit_metadata=json.dumps(safe_metadata, default=str),
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def record_for_request(
        self,
        *,
        action: str,
        current_user: Optional[User] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None,
        request: Optional[Any] = None,
    ) -> AuditLog:
        ip_address = None
        user_agent = None
        if request is not None:
            ip_address = self._client_ip(request)
            user_agent = request.headers.get("user-agent") if hasattr(request, "headers") else None

        return self.record(
            action=action,
            actor_user_id=current_user.id if current_user else None,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        safe: Dict[str, Any] = {}
        for key, value in metadata.items():
            if key.lower() in {"password", "password_hash", "jwt", "token", "api_key", "secret", "authorization", "prompt", "document_content"}:
                continue
            if isinstance(value, (dict, list, tuple, set)):
                safe[key] = json.loads(json.dumps(value, default=str))
            else:
                safe[key] = value
        return safe

    @staticmethod
    def _client_ip(request: Any) -> Optional[str]:
        if hasattr(request, "client") and request.client is not None:
            return getattr(request.client, "host", None)
        return None


def create_audit_service(db: Session) -> AuditService:
    return AuditService(db)
