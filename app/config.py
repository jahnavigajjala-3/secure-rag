import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load the project .env file reliably
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Support both the project root and a frontend-local env file when the app is launched
# from a different working directory.
load_dotenv(Path(__file__).resolve().parents[1] / "frontend" / ".env")

def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.ENVIRONMENT = os.getenv("APP_ENV", "development").strip().lower()
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./secure_rag.db")
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
            os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
            or os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
            or "60"
        )
        self.ADMIN_BOOTSTRAP_EMAIL = os.getenv("ADMIN_BOOTSTRAP_EMAIL")
        self.ADMIN_BOOTSTRAP_PASSWORD = os.getenv("ADMIN_BOOTSTRAP_PASSWORD")
        self.ADMIN_SIGNUP_KEY = (
            os.getenv("ADMIN_SIGNUP_KEY")
            or os.getenv("ADMIN_INVITATION_CODE")
            or "secure_rag_admin_invite_2026"
        )
        self.CORS_ALLOWED_ORIGINS = [
            origin.strip()
            for origin in (os.getenv("CORS_ALLOWED_ORIGINS") or os.getenv("ALLOWED_ORIGINS") or "http://localhost:3000,http://localhost:5173").split(",")
            if origin.strip()
        ]
        self.CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
        self.CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        self.EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION") or "384")
        self.UPLOAD_DIRECTORY = Path(os.getenv("UPLOAD_DIRECTORY", "./data/documents")).resolve()

    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    def validate_runtime(self) -> None:
        if self.is_production():
            if not self.DATABASE_URL:
                raise RuntimeError("DATABASE_URL is required in production.")
            if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY in {"", "changeme", "secure_rag_dev_jwt_secret_key_change_in_production"}:
                raise RuntimeError("JWT_SECRET_KEY must be set to a strong secret in production.")
            if len(self.JWT_SECRET_KEY) < 32:
                raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters in production.")
            if not self.CORS_ALLOWED_ORIGINS:
                raise RuntimeError("CORS_ALLOWED_ORIGINS must be configured explicitly in production.")
            if not self.GEMINI_API_KEY:
                raise RuntimeError("GEMINI_API_KEY is required in production for grounded answer generation.")
        else:
            if not self.JWT_SECRET_KEY:
                self.JWT_SECRET_KEY = "secure_rag_dev_jwt_secret_key_change_in_production"

    @property
    def allowed_origins(self) -> List[str]:
        return self.CORS_ALLOWED_ORIGINS


settings = Settings()
settings.validate_runtime()
