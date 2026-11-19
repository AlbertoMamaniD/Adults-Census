from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ConfusionMatrix(BaseModel):
    tn: int = Field(..., description="Verdaderos Negativos (<=50K clasificados como <=50K)")
    fp: int = Field(..., description="Falsos Positivos (<=50K clasificados como >50K - Riesgo Mora Crítico)")
    fn: int = Field(..., description="Falsos Negativos (>50K clasificados como <=50K - Costo Oportunidad)")
    tp: int = Field(..., description="Verdaderos Positivos (>50K clasificados como >50K - Clientes Solventes)")


class MetricsDetails(BaseModel):
    mcc: float = Field(..., description="Matthews Correlation Coefficient (Métrica Principal >= 0.55)")
    precision: float = Field(..., description="Precisión en clase positiva (>= 0.75)")
    recall: float = Field(..., description="Sensibilidad / Recall en clase positiva (>= 0.60)")
    roc_auc: float = Field(..., description="Área bajo la curva ROC (>= 0.90)")
    accuracy: float = Field(..., description="Exactitud global")
    f1: Optional[float] = Field(default=None, description="F1-Score armónico")
    confusion_matrix: ConfusionMatrix = Field(..., description="Matriz de confusión detallada")
    expected_cost: Optional[float] = Field(default=None, description="Costo asimétrico esperado (3*FP + 1*FN)")


class ModelMetricsResponse(BaseModel):
    model_version: str = Field(..., description="Versión inmutable del modelo activo")
    model_name: str = Field(..., description="Nombre del algoritmo clasificador")
    trained_at: str = Field(..., description="Fecha y hora de entrenamiento (ISO 8601 UTC)")
    threshold: float = Field(..., description="Umbral de decisión calibrado")
    metrics: MetricsDetails = Field(..., description="Métricas de desempeño validadas")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Hiperparámetros relevantes")
