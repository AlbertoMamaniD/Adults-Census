from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class UploadDatasetResponse(BaseModel):
    status: str = Field(..., description="Estado de la operación", examples=["success"])
    filename: str = Field(..., description="Nombre del archivo procesado", examples=["adult_actualizado.csv"])
    rows_ingested: int = Field(..., description="Cantidad de registros leídos y validados", examples=[32561])
    dataset_id: int = Field(..., description="ID asignado en base de datos", examples=[1])
    message: str = Field(..., description="Mensaje explicativo del proceso", examples=["Archivo validado y registrado en training_datasets."])


class RetrainResponse(BaseModel):
    status: str = Field(..., description="Estado del pipeline", examples=["success"])
    message: str = Field(..., description="Resumen de ejecución", examples=["Pipeline CRISP-ML(Q) completado con éxito."])
    new_model_version: str = Field(..., description="Identificador de la nueva versión de artefacto generada", examples=["v20261118153000"])
    updated_metrics: Dict[str, Any] = Field(..., description="Métricas de evaluación del nuevo modelo entrenado")
    threshold: Optional[float] = Field(default=None, description="Nuevo umbral robusto calibrado")


class RetrainStatusUpdate(BaseModel):
    stage: str = Field(..., description="Fase del pipeline (preprocessing, training, evaluating, completed, error)")
    progress: int = Field(..., ge=0, le=100, description="Porcentaje de avance (0-100)")
    message: str = Field(..., description="Detalle textual del paso actual")
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Datos adicionales o métricas intermedias")
