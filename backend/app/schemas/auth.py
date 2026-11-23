from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="Nombre de usuario del analista o administrador", examples=["analyst"])
    password: str = Field(..., description="Contraseña de acceso", examples=["********"])


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="Token Bearer JWT para autenticar peticiones")
    token_type: str = Field(default="bearer", description="Tipo de token")
    expires_in_minutes: int = Field(default=1440, description="Tiempo de vigencia en minutos")
    username: str = Field(..., description="Usuario autenticado")
