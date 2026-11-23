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
    # Validar que las credenciales administrativas estén configuradas (Qodo Finding 4)
    if not settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Acceso administrativo deshabilitado: credenciales no configuradas para este entorno.",
        )

    # Comparación segura en tiempo constante con codificación utf-8 para caracteres no ASCII (Qodo Finding 15)
    input_user_bytes = credentials.username.strip().encode("utf-8")
    expected_user_bytes = settings.ADMIN_USERNAME.encode("utf-8")
    input_pass_bytes = credentials.password.encode("utf-8")
    expected_pass_bytes = settings.ADMIN_PASSWORD.encode("utf-8")

    is_user_valid = secrets.compare_digest(input_user_bytes, expected_user_bytes)
    is_pass_valid = secrets.compare_digest(input_pass_bytes, expected_pass_bytes)

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
