import os
import re
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin_user, get_current_user
from app.database.database import get_db
from app.database.models import Document, Role, User
from app.ingestion.pipeline import ingest_document_by_id
from app.schemas.document import DocumentAccessUpdateRequest, DocumentResponse
from app.vectorstore.store import delete_chunks_by_document_id

router = APIRouter(prefix="/api/documents", tags=["Document Management"])
admin_router = APIRouter(prefix="/admin/documents", tags=["Admin Document Management"])

DOCUMENTS_DIR = Path(__file__).parent.parent.parent / "data" / "documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
}
MAX_FILE_SIZE = 50 * 1024 * 1024


def safe_filename(filename: str) -> str:
    """Generate a filesystem-safe name without trusting the original uploaded name."""
    if not filename or not filename.strip():
        raise ValueError("Uploaded filename is required.")

    sanitized = os.path.basename(filename).strip()
    sanitized = sanitized.replace("/", "_").replace("\\", "_")
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", sanitized)
    sanitized = sanitized.strip("._")
    if not sanitized or sanitized in {".", ".."}:
        raise ValueError("Uploaded filename is unsafe.")
    return sanitized


def validate_upload(file: UploadFile, content_type: Optional[str] = None) -> Tuple[Path, str, str, int]:
    """Validate file extension, MIME type, and size before storing."""
    if file is None or not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must have a valid filename.")

    original_name = file.filename
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    if content_type:
        allowed_types = ALLOWED_MIME_TYPES.get(ext, set())
        if allowed_types and content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unexpected content type '{content_type}' for extension '{ext}'.",
            )

    safe_base = safe_filename(original_name)
    safe_name = f"{uuid.uuid4().hex}_{safe_base}"
    storage_path = DOCUMENTS_DIR / safe_name

    chunk_size = 1024 * 1024
    total_size = 0
    file.file.seek(0)
    with storage_path.open("wb") as buffer:
        while True:
            chunk = file.file.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                buffer.close()
                os.remove(storage_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE // (1024 * 1024)} MB.",
                )
            buffer.write(chunk)
    file.file.seek(0)

    return storage_path, original_name, safe_base, total_size


def format_doc_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename or doc.original_filename or "unknown",
        file_size=doc.file_size,
        chunk_count=doc.chunk_count,
        status=doc.status,
        uploaded_at=doc.uploaded_at.strftime("%Y-%m-%d %H:%M") if doc.uploaded_at else "",
        uploaded_by=doc.uploaded_by.username if doc.uploaded_by else None,
        accessible_roles=[role.name for role in doc.roles],
    )


def resolve_roles_by_names_or_ids(role_inputs: List[str], db: Session) -> List[Role]:
    resolved_roles: List[Role] = []
    for item in role_inputs:
        item_clean = str(item).strip()
        if not item_clean:
            continue
        role_obj = db.query(Role).filter((Role.id == item_clean) | (Role.name.ilike(item_clean))).first()
        if not role_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{item}' is invalid or does not exist.",
            )
        if role_obj not in resolved_roles:
            resolved_roles.append(role_obj)
    return resolved_roles


def get_document_or_404(doc_id: str, db: Session) -> Document:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with id '{doc_id}' not found.")
    return doc


def create_document_record(
    *,
    file: UploadFile,
    uploaded_by: User,
    db: Session,
    allowed_roles: Optional[List[str]] = None,
) -> Document:
    storage_path, original_name, safe_name, file_size = validate_upload(file, file.content_type)

    target_roles: List[Role] = []
    if allowed_roles:
        target_roles = resolve_roles_by_names_or_ids(allowed_roles, db)

    document = Document(
        name=safe_name,
        filename=safe_name,
        original_filename=original_name,
        storage_path=str(storage_path),
        file_path=str(storage_path),
        file_size=file_size,
        chunk_count=0,
        status="PROCESSING",
        uploaded_by_id=uploaded_by.id,
    )
    document.roles.extend(target_roles)

    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        ingest_document_by_id(document.id, db)
    except Exception as exc:
        safe_error = "Document processing failed. Please contact an administrator for details."
        document.status = "FAILED"
        document.error_message = safe_error
        db.commit()
        db.refresh(document)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_error,
        ) from exc

    db.refresh(document)
    return document


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    allowed_roles: Optional[List[str]] = Form(None),
    role_ids: Optional[List[str]] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_values = allowed_roles or role_ids or []
    doc = create_document_record(file=file, uploaded_by=current_user, db=db, allowed_roles=role_values)
    return format_doc_response(doc)


@admin_router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def admin_upload_document(
    file: UploadFile = File(...),
    allowed_roles: Optional[List[str]] = Form(None),
    role_ids: Optional[List[str]] = Form(None),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    role_values = allowed_roles or role_ids or []
    doc = create_document_record(file=file, uploaded_by=current_user, db=db, allowed_roles=role_values)
    return format_doc_response(doc)


@router.get("", response_model=List[DocumentResponse])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if "admin" not in {role.name.lower() for role in current_user.roles}:
        role_ids = [role.id for role in current_user.roles]
        if not role_ids:
            return []
        docs = (
            db.query(Document)
            .join(Document.roles)
            .filter(Role.id.in_(role_ids))
            .filter(Document.status == "READY")
            .distinct()
            .order_by(Document.uploaded_at.desc())
            .all()
        )
        return [format_doc_response(doc) for doc in docs]

    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [format_doc_response(doc) for doc in docs]


@admin_router.get("", response_model=List[DocumentResponse])
def admin_list_documents(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [format_doc_response(doc) for doc in docs]


@router.get("/my", response_model=List[DocumentResponse])
def list_my_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_ids = [role.id for role in current_user.roles]
    if not role_ids:
        return []

    docs = (
        db.query(Document)
        .join(Document.roles)
        .filter(Role.id.in_(role_ids))
        .filter(Document.status == "READY")
        .distinct()
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    return [format_doc_response(doc) for doc in docs]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = get_document_or_404(document_id, db)
    if "admin" not in {role.name.lower() for role in current_user.roles}:
        role_ids = [role.id for role in current_user.roles]
        if not role_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this document.")
        allowed = (
            db.query(Document.id)
            .join(Document.roles)
            .filter(Role.id.in_(role_ids))
            .filter(Document.id == document_id)
            .filter(Document.status == "READY")
            .distinct()
            .first()
        )
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this document.")
    return format_doc_response(doc)


@admin_router.get("/{document_id}", response_model=DocumentResponse)
def admin_get_document(
    document_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    doc = get_document_or_404(document_id, db)
    return format_doc_response(doc)


@admin_router.delete("/{document_id}")
def admin_delete_document(
    document_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    doc = get_document_or_404(document_id, db)

    try:
        delete_chunks_by_document_id(doc.id)
    except Exception:
        pass

    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass

    doc.roles.clear()
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully", "id": document_id}


@admin_router.post("/{document_id}/roles/{role_id}", response_model=DocumentResponse)
def admin_assign_document_role(
    document_id: str,
    role_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    doc = get_document_or_404(document_id, db)
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role with id '{role_id}' not found.")
    if role in doc.roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{role.name}' is already assigned to document '{doc.filename}'.")
    doc.roles.append(role)
    db.commit()
    db.refresh(doc)
    return format_doc_response(doc)


@admin_router.delete("/{document_id}/roles/{role_id}", response_model=DocumentResponse)
def admin_remove_document_role(
    document_id: str,
    role_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    doc = get_document_or_404(document_id, db)
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role with id '{role_id}' not found.")
    if role not in doc.roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{role.name}' is not assigned to document '{doc.filename}'.")
    doc.roles.remove(role)
    db.commit()
    db.refresh(doc)
    return format_doc_response(doc)


@admin_router.put("/{document_id}/access", response_model=DocumentResponse)
def admin_update_document_access(
    document_id: str,
    payload: DocumentAccessUpdateRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    doc = get_document_or_404(document_id, db)
    if not payload.allowed_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one allowed role must be specified.")

    new_roles = resolve_roles_by_names_or_ids(payload.allowed_roles, db)
    doc.roles.clear()
    doc.roles.extend(new_roles)
    db.commit()
    db.refresh(doc)
    return format_doc_response(doc)
