import os
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User, Role, Document
from app.auth.dependencies import get_current_user, get_current_admin_user
from app.schemas.document import DocumentResponse, DocumentAccessUpdateRequest
from app.ingestion.loader import load_document
from app.ingestion.chunker import chunk_document
from app.ingestion.embedder import embed_texts
from app.ingestion.pipeline import ingest_document_by_id
from app.vectorstore.store import add_chunks, delete_chunks_by_document_id

router = APIRouter(prefix="/api/documents", tags=["Document Management"])
admin_router = APIRouter(prefix="/admin/documents", tags=["Admin Document Management"])

DOCUMENTS_DIR = Path(__file__).parent.parent.parent / "data" / "documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".doc", ".md", ".csv", ".json"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB limit


def format_doc_response(doc: Document) -> DocumentResponse:
    """Helper to convert SQLAlchemy Document model to Pydantic DocumentResponse."""
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_size=doc.file_size,
        chunk_count=doc.chunk_count,
        status=doc.status,
        uploaded_at=doc.uploaded_at.strftime("%Y-%m-%d %H:%M") if doc.uploaded_at else "",
        uploaded_by=doc.uploaded_by.username if doc.uploaded_by else None,
        accessible_roles=[r.name for r in doc.roles],
    )


def resolve_roles_by_names_or_ids(role_inputs: List[str], db: Session) -> List[Role]:
    """
    Validate and retrieve Role records for a list of role names or role IDs.
    Raises HTTP 400 Bad Request if any provided role does not exist in RBAC.
    """
    resolved_roles: List[Role] = []
    for item in role_inputs:
        item_clean = item.strip()
        if not item_clean:
            continue
        role_obj = (
            db.query(Role)
            .filter((Role.id == item_clean) | (Role.name.ilike(item_clean)))
            .first()
        )
        if not role_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{item}' is invalid or does not exist."
            )
        if role_obj not in resolved_roles:
            resolved_roles.append(role_obj)
    return resolved_roles


# ---------------------------------------------------------------------------
# ADMIN DOCUMENT ENDPOINTS (/admin/documents)
# ---------------------------------------------------------------------------

@admin_router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@admin_router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def admin_upload_document(
    file: UploadFile = File(...),
    allowed_roles: Optional[List[str]] = Form(None),
    role_ids: Optional[List[str]] = Form(None),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin-only document upload endpoint.
    Saves file to disk, creates PostgreSQL metadata record, validates and binds allowed roles.
    Enforces admin authorization (HTTP 403 for non-admin users).
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename."
        )

    # 1. Validate File Extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # 2. Save File & Measure Size
    target_path = DOCUMENTS_DIR / file.filename
    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(target_path)
    if file_size > MAX_FILE_SIZE:
        if os.path.exists(target_path):
            os.remove(target_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE // (1024 * 1024)} MB."
        )

    # 3. Resolve & Validate Allowed Roles
    raw_roles = allowed_roles or role_ids or []
    if raw_roles:
        target_roles = resolve_roles_by_names_or_ids(raw_roles, db)
    else:
        # Default to 'admin' role if none supplied
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin")
            db.add(admin_role)
            db.commit()
        target_roles = [admin_role]

    # 4. Create Document Record with UPLOADED status
    new_doc = Document(
        filename=file.filename,
        file_path=str(target_path.resolve()),
        file_size=file_size,
        chunk_count=0,
        status="UPLOADED",
        uploaded_by_id=admin_user.id,
    )
    new_doc.roles.extend(target_roles)

    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # 5. Run Document Ingestion Pipeline (transitions: UPLOADED -> PROCESSING -> READY / FAILED)
    try:
        ingest_document_by_id(new_doc.id, db)
    except Exception as e:
        print(f"Warning: Document ingestion pipeline encountered an error for {file.filename}: {e}")

    db.refresh(new_doc)
    return format_doc_response(new_doc)


@admin_router.get("", response_model=List[DocumentResponse])
def admin_list_documents(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin-only endpoint to list all documents with full metadata and access policies.
    Returns HTTP 403 Forbidden for non-admin users.
    """
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [format_doc_response(d) for d in docs]


@admin_router.put("/{doc_id}/access", response_model=DocumentResponse)
def update_document_access_policy(
    doc_id: str,
    payload: DocumentAccessUpdateRequest,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin-only endpoint to replace/update a document's allowed access policy roles.
    Enforces role validation (HTTP 400 for invalid roles) and returns 404 if document not found.
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id '{doc_id}' not found."
        )

    if not payload.allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one allowed role must be specified."
        )

    new_roles = resolve_roles_by_names_or_ids(payload.allowed_roles, db)
    doc.roles.clear()
    doc.roles.extend(new_roles)

    db.commit()
    db.refresh(doc)
    return format_doc_response(doc)


@admin_router.delete("/{doc_id}")
def admin_delete_document(
    doc_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin-only document deletion endpoint.
    Deletes DB record, role bindings, vector store chunks, and physical file.
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id '{doc_id}' not found."
        )

    # 1. Delete ChromaDB vector chunks
    try:
        delete_chunks_by_document_id(doc.id)
        if doc.filename:
            delete_chunks_by_document_id(Path(doc.filename).stem)
    except Exception as e:
        print(f"Warning: Failed to delete vector chunks: {e}")

    # 2. Delete Physical File
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            print(f"Warning: Failed to remove physical file {doc.file_path}: {e}")

    # 3. Delete Document record
    db.delete(doc)
    db.commit()

    return {"message": "Document deleted successfully", "id": doc_id}


# ---------------------------------------------------------------------------
# GENERAL/FALLBACK DOCUMENT ENDPOINTS (/api/documents)
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document_api(
    file: UploadFile = File(...),
    role_ids: Optional[List[str]] = Form(None),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Backward compatible upload endpoint for /api/documents/upload."""
    return admin_upload_document(
        file=file,
        allowed_roles=role_ids,
        admin_user=admin_user,
        db=db
    )


@router.get("", response_model=List[DocumentResponse])
def list_documents_api(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """General document list endpoint for authenticated users."""
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [format_doc_response(d) for d in docs]


@router.put("/{doc_id}/access", response_model=DocumentResponse)
def update_document_access_api(
    doc_id: str,
    payload: DocumentAccessUpdateRequest,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Backward compatible access update endpoint."""
    return update_document_access_policy(doc_id=doc_id, payload=payload, admin_user=admin_user, db=db)


@router.post("/{doc_id}/roles/{role_id}", response_model=DocumentResponse)
def assign_role_to_document_api(
    doc_id: str,
    role_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Assign individual role to document."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id '{doc_id}' not found."
        )
    roles = resolve_roles_by_names_or_ids([role_id], db)
    if roles[0] in doc.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{roles[0].name}' is already bound to document '{doc.filename}'."
        )
    doc.roles.append(roles[0])
    db.commit()
    db.refresh(doc)
    return format_doc_response(doc)


@router.delete("/{doc_id}/roles/{role_id}", response_model=DocumentResponse)
def remove_role_from_document_api(
    doc_id: str,
    role_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Remove individual role from document."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id '{doc_id}' not found."
        )
    roles = resolve_roles_by_names_or_ids([role_id], db)
    if roles[0] not in doc.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{roles[0].name}' is not assigned to document '{doc.filename}'."
        )
    doc.roles.remove(roles[0])
    db.commit()
    db.refresh(doc)
    return format_doc_response(doc)


@router.delete("/{doc_id}")
def delete_document_api(
    doc_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Backward compatible delete endpoint."""
    return admin_delete_document(doc_id=doc_id, admin_user=admin_user, db=db)
