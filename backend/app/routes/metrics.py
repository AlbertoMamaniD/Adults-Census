from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import ModelRun
from app.schemas.metrics import ConfusionMatrix, MetricsDetails, ModelMetricsResponse
from app.services.ml_service import ml_service

router = APIRouter(prefix="", tags=["Métricas y MLOps"])


@router.get(
    "/metrics",
    response_model=ModelMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Métricas de desempeño del modelo activo en producción",
    description=(
        "### Reporte de Evaluación Metodológica CRISP-ML(Q)\n\n"
        "Retorna los indicadores de calidad del modelo activo evaluados en el conjunto de prueba independiente (6.508 registros):\n\n"
        "- **MCC (Matthews Correlation Coefficient):** Métrica principal obligatoria para datasets desbalanceados ($MCC = 0.6192 \\ge 0.55$).\n"
        "- **Precisión:** Proporción de clientes clasificados como solventes que realmente lo son ($78.40\\% \\ge 75\\%$).\n"
        "- **Sensibilidad / Recall:** Proporción de clientes solventes detectados ($62.50\\% \\ge 60\\%$).\n"
        "- **ROC-AUC:** Capacidad discriminativa global del clasificador ($0.9217 \\ge 0.90$).\n"
        "- **Matriz de Confusión:** Desglose exacto de $TN$ (4.670), $FP$ (270), $FN$ (588) y $TP$ (980).\n"
        "- **Umbral Calibrado:** $\\theta = 0.77$, optimizado para penalizar 3 veces más el Falso Positivo que el Falso Negativo."
    ),
    responses={
        200: {"description": "Reporte de métricas técnicas y parámetros del modelo activo en producción."},
    },
)
def get_model_metrics(db: Session = Depends(get_db)):
    # Intentar obtener de la base de datos primero si hay un run activo registrado
    active_run = db.query(ModelRun).filter(ModelRun.is_active == True).order_by(ModelRun.id.desc()).first()
    
    if active_run:
        metrics_dict = active_run.metrics
        cm_data = metrics_dict.get("confusion_matrix", {})
        return ModelMetricsResponse(
            model_version=active_run.model_version,
            model_name=active_run.model_name,
            trained_at=active_run.trained_at.isoformat() if hasattr(active_run.trained_at, "isoformat") else str(active_run.trained_at),
            threshold=round(float(active_run.threshold), 4),
            metrics=MetricsDetails(
                mcc=round(float(metrics_dict.get("mcc", 0.0)), 4),
                precision=round(float(metrics_dict.get("precision", 0.0)), 4),
                recall=round(float(metrics_dict.get("recall", 0.0)), 4),
                roc_auc=round(float(metrics_dict.get("roc_auc", 0.0)), 4),
                accuracy=round(float(metrics_dict.get("accuracy", 0.0)), 4),
                f1=round(float(metrics_dict.get("f1", 0.0)), 4) if "f1" in metrics_dict else None,
                confusion_matrix=ConfusionMatrix(
                    tn=int(cm_data.get("tn", 0)),
                    fp=int(cm_data.get("fp", 0)),
                    fn=int(cm_data.get("fn", 0)),
                    tp=int(cm_data.get("tp", 0)),
                ),
                expected_cost=metrics_dict.get("expected_cost"),
            ),
            parameters=active_run.parameters or {},
        )

    # Fallback al archivo metadata_latest.json
    meta = ml_service.get_metrics()
    metrics_dict = meta.get("metrics", {})
    return ModelMetricsResponse(
        model_version=meta.get("model_version", "v_latest"),
        model_name=meta.get("model_name", "Gradient boosting"),
        trained_at=meta.get("trained_at", ""),
        threshold=round(float(meta.get("threshold", 0.77)), 4),
        metrics=MetricsDetails(
            mcc=round(float(metrics_dict.get("mcc", 0.0)), 4),
            precision=round(float(metrics_dict.get("precision", 0.0)), 4),
            recall=round(float(metrics_dict.get("recall", 0.0)), 4),
            roc_auc=round(float(metrics_dict.get("roc_auc", 0.0)), 4),
            accuracy=round(float(metrics_dict.get("accuracy", 0.0)), 4),
            f1=round(float(metrics_dict.get("f1", 0.0)), 4) if "f1" in metrics_dict else None,
            confusion_matrix=ConfusionMatrix(
                tn=int(metrics_dict.get("true_negatives", metrics_dict.get("confusion_matrix", {}).get("tn", 0))),
                fp=int(metrics_dict.get("false_positives", metrics_dict.get("confusion_matrix", {}).get("fp", 0))),
                fn=int(metrics_dict.get("false_negatives", metrics_dict.get("confusion_matrix", {}).get("fn", 0))),
                tp=int(metrics_dict.get("true_positives", metrics_dict.get("confusion_matrix", {}).get("tp", 0))),
            ),
            expected_cost=metrics_dict.get("expected_cost"),
        ),
        parameters=meta.get("parameters", {}),
    )
