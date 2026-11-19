from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.prediction import PredictionInput, PredictionResponse
from app.services.auth_service import get_optional_user
from app.services.ml_service import ml_service

router = APIRouter(prefix="", tags=["Inferencia en Tiempo Real"])


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Inferencia en tiempo real para precalificación crediticia",
    description=(
        "### Evaluación de Solvencia Crediticia Simulada\n\n"
        "Este endpoint evalúa los 12 atributos censales de un solicitante utilizando el pipeline serializado en producción.\n\n"
        "**Flujo de Negocio:**\n"
        "1. **Validación:** Comprueba tipos y rangos de edad (17-100), horas (1-100), capital y variables categóricas.\n"
        "2. **Transformación:** Escala variables numéricas y aplica One-Hot Encoding tolerando categorías desconocidas (`handle_unknown='ignore'`).\n"
        "3. **Inferencia:** El clasificador `HistGradientBoostingClassifier` calcula la probabilidad $P(\\text{income} > \\$50\\text{K})$.\n"
        "4. **Regla de Decisión:** Aplica el umbral robusto calibrado **$\\theta = 0.77$** (determinado para minimizar la función de costo asimétrica $3\\times FP + 1\\times FN$):\n"
        "   - Si $P \\ge 0.77$: Clasifica como `>50K` (Califica para producto crediticio de alto monto).\n"
        "   - Si $P < 0.77$: Clasifica como `<=50K` (No califica por riesgo crediticio o ingresos insuficientes).\n"
        "5. **Auditoría:** Persiste el registro transaccional en la tabla `predictions` de Supabase PostgreSQL con su latencia en ms."
    ),
    responses={
        200: {
            "description": "Inferencia exitosa. Devuelve la clase predicha, probabilidad, umbral aplicado y recomendación de riesgo.",
        },
        422: {
            "description": "Error de validación. Los campos enviados violan los límites de rango o formato de esquema.",
        },
        429: {
            "description": "Rate limit excedido. Se superó el límite de 120 peticiones por minuto por IP.",
        },
    },
)
def predict(
    payload: PredictionInput,
    db: Session = Depends(get_db),
    user: dict = Depends(get_optional_user),
):
    prediction = ml_service.predict(input_data=payload, db=db)
    return prediction
