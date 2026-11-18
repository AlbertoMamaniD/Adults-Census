import os
from pathlib import Path
import secrets
from dotenv import load_dotenv

# Determinar raiz del proyecto y cargar variables de entorno desde .env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    PROJECT_NAME: str = "Servicio de Precalificación Crediticia - CRISP-ML(Q)"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Rutas del repositorio
    REPO_ROOT: Path = BASE_DIR
    ARTIFACTS_DIR: Path = BASE_DIR / "artifacts"
    DATA_DIR: Path = BASE_DIR / "data"
    
    # Seguridad JWT: clave criptográfica leída del entorno o generada efímeramente para desarrollo
    SECRET_KEY: str = (
        os.environ.get("JWT_SECRET_KEY")
        or os.environ.get("SECRET_KEY")
        or secrets.token_urlsafe(32)
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas
    
    # Credenciales de usuario para pruebas y acceso analítico
    ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME") or "analyst_admin"
    ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD") or "dev_auth_token"
    
    # Base de Datos Supabase (PostgreSQL)
    @property
    def DATABASE_URL(self) -> str:
        url = os.environ.get("SUPABASE_DB_URL", "").strip()
        if url:
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            return url
        # Fallback local SQLite si no hay credenciales
        local_db = self.ARTIFACTS_DIR / "local_database.db"
        return f"sqlite:///{local_db}"


settings = Settings()
