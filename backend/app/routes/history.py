from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import Prediction
from app.schemas.history import PredictionHistoryItem
from app.services.auth_service import get_optional_user

router = APIRouter(prefix="", tags=["Historial de Predicciones"])


@router.get(
    "/history",
    response_model=List[PredictionHistoryItem],
    status_code=status.HTTP_200_OK,
    summary="Consultar historial de inferencias realizadas",
    description=(
        "### Auditoría Transaccional de Decisiones Crediticias\n\n"
        "Recupera las predicciones registradas en la base de datos Supabase PostgreSQL en orden cronológico descendente.\n\n"
        "**Utilidad:**\n"
        "- **Trazabilidad:** Auditar qué recomendación se le otorgó a un solicitante y qué atributos demográficos tenía.\n"
        "- **Monitoreo de Drift:** Permite al frontend o a analistas detectar cambios en la distribución de probabilidades.\n"
        "- **Paginación Eficiente:** Parámetros `limit` (1 a 200) y `offset` (desplazamiento)."
    ),
    responses={
        200: {"description": "Lista de predicciones históricas recuperadas exitosamente."},
        422: {"description": "Parámetros de consulta (limit u offset) fuera del rango permitido."},
    },
)
def get_prediction_history(
    limit: int = Query(50, ge=1, le=200, description="Cantidad máxima de registros a recuperar (1-200)"),
    offset: int = Query(0, ge=0, description="Desplazamiento inicial para paginación"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_optional_user),
):
    query = (
        db.query(Prediction)
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
        .offset(offset)
        .limit(limit)
    )
    records = query.all()
    return records
