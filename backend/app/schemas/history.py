from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel, Field


class PredictionHistoryItem(BaseModel):
    id: int = Field(..., description="ID único de la predicción")
    created_at: datetime = Field(..., description="Marca temporal de la inferencia (UTC)")
    model_version: str = Field(..., description="Versión del modelo empleada")
    input_data: Dict[str, Any] = Field(..., description="Datos demográficos y socioeconómicos del cliente")
    predicted_class: str = Field(..., description="Clase predicha ('>50K' o '<=50K')")
    probability: float = Field(..., description="Probabilidad estimada de pertenencia a clase positiva")
    latency_ms: float = Field(..., description="Latencia de procesamiento en milisegundos")

    class Config:
        from_attributes = True


class HistoryResponse(BaseModel):
    total: int = Field(..., description="Cantidad total de inferencias registradas")
    limit: int = Field(..., description="Límite por página")
    offset: int = Field(..., description="Desplazamiento aplicado")
    items: List[PredictionHistoryItem] = Field(..., description="Lista de inferencias históricas")
