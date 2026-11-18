import secrets
from fastapi import APIRouter, HTTPException, status
from app.config import settings
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import create_access_token

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión y obtener token JWT Bearer",
    description="Valida las credenciales del usuario y genera un token JWT Bearer para acceder a los endpoints protegidos.",
)
def login(credentials: LoginRequest):
    # Comparación segura en tiempo constante para mitigar ataques de temporización (timing attacks)
    is_user_valid = secrets.compare_digest(credentials.username.strip(), settings.ADMIN_USERNAME)
    is_pass_valid = secrets.compare_digest(credentials.password, settings.ADMIN_PASSWORD)

    if is_user_valid and is_pass_valid:
        access_token = create_access_token(data={"sub": credentials.username, "role": "admin"})
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            username=credentials.username,
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales de acceso incorrectas. Verifique su usuario y contraseña.",
        headers={"WWW-Authenticate": "Bearer"},
    )
