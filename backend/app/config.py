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
    
    # Seguridad JWT: clave criptográfica leída del entorno o persistida en archivo para desarrollo (Qodo Finding 16)
    @property
    def SECRET_KEY(self) -> str:
        key = os.environ.get("JWT_SECRET_KEY") or os.environ.get("SECRET_KEY")
        if key:
            return key
        if os.environ.get("ENV") in ("production", "prod"):
            raise RuntimeError("CRÍTICO: JWT_SECRET_KEY debe estar configurado explícitamente en el entorno de producción.")
        
        # En desarrollo / local: persistir en archivo para evitar invalidar tokens en reinicios o entre workers
        secret_file = self.ARTIFACTS_DIR / ".jwt_secret"
        if secret_file.exists():
            try:
                stored = secret_file.read_text(encoding="utf-8").strip()
                if stored:
                    return stored
            except Exception:
                pass
        new_secret = secrets.token_urlsafe(32)
        try:
            self.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
            secret_file.write_text(new_secret, encoding="utf-8")
        except Exception:
            pass
        return new_secret

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas
    
    # Credenciales de usuario para acceso analítico (Qodo Finding 4)
    @property
    def ADMIN_USERNAME(self) -> str:
        val = os.environ.get("ADMIN_USERNAME")
        if val:
            return val
        if os.environ.get("ENV") in ("production", "prod"):
            return ""  # En producción no se permite fallback predeterminado
        return "analyst_admin"

    @property
    def ADMIN_PASSWORD(self) -> str:
        val = os.environ.get("ADMIN_PASSWORD")
        if val:
            return val
        if os.environ.get("ENV") in ("production", "prod"):
            return ""  # En producción no se permite fallback predeterminado
        return "dev_auth_token"
    
    # Base de Datos Supabase (PostgreSQL)
    @property
    def DATABASE_URL(self) -> str:
        # Modo de prueba: Aislar completamente para evitar mutación en bases de datos compartidas (Qodo Finding 3)
        if os.environ.get("ENV") == "testing" or os.environ.get("TESTING") == "1":
            test_url = os.environ.get("TEST_DB_URL") or os.environ.get("SUPABASE_DB_URL", "")
            if test_url and "sqlite" in test_url.lower():
                return test_url
            local_test_db = self.ARTIFACTS_DIR / "test_isolated.db"
            return f"sqlite:///{local_test_db.as_posix()}"

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
