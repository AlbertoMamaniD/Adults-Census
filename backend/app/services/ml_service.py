import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
import joblib
import pandas as pd
from sqlalchemy.orm import Session
from app.config import settings
from app.database.models import Prediction
from app.schemas.prediction import PredictionInput, PredictionResponse

logger = logging.getLogger("ml_service")


class MLService:
    """Servicio singleton para inferencia, gestión de modelo en memoria y auditoría."""

    def __init__(self) -> None:
        self.model: Optional[Any] = None
        self.metadata: Dict[str, Any] = {}
        self.model_version: str = "unknown"
        self.threshold: float = 0.77
        self.load_active_model(raise_on_missing=False)

    def load_active_model(self, raise_on_missing: bool = False) -> None:
        """Carga en memoria el artefacto binario y los metadatos más recientes."""
        model_path = settings.ARTIFACTS_DIR / "model_latest.joblib"
        metadata_path = settings.ARTIFACTS_DIR / "metadata_latest.json"

        if not model_path.exists():
            logger.warning(f"Artefacto de modelo no encontrado en: {model_path}. Servicio en espera de inicialización o reentrenamiento.")
            if raise_on_missing:
                raise FileNotFoundError(f"No se encontró el artefacto de modelo en {model_path}")
            self.model = None
            return

        logger.info(f"Cargando modelo serializado desde {model_path}...")
        self.model = joblib.load(model_path)

        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
            self.model_version = self.metadata.get("model_version", "v_latest")
            self.threshold = float(self.metadata.get("threshold", 0.77))
            logger.info(
                f"Metadatos cargados con éxito. Versión: {self.model_version}, Umbral Calibrado: {self.threshold:.4f}"
            )
        else:
            logger.warning(f"Metadatos no encontrados en {metadata_path}. Usando valores por defecto.")
            self.model_version = "v_default"
            self.threshold = 0.77

    def predict(self, input_data: PredictionInput, db: Optional[Session] = None) -> PredictionResponse:
        """Ejecuta inferencia en tiempo real, mide latencia y persiste la predicción en base de datos."""
        if self.model is None:
            self.load_active_model(raise_on_missing=False)
            if self.model is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="El modelo de inferencia no está disponible en este momento. Por favor ejecute el reentrenamiento para inicializarlo.",
                )

        data_dict = input_data.to_inference_dict()
        df = pd.DataFrame([data_dict])

        # Medición rigurosa de latencia
        start_time = time.perf_counter()
        proba_matrix = self.model.predict_proba(df)
        end_time = time.perf_counter()
        latency_ms = round((end_time - start_time) * 1000, 2)

        # Probabilidad de clase positiva (>50K)
        probability = float(proba_matrix[0, 1])
        predicted_class = ">50K" if probability >= self.threshold else "<=50K"

        # Recomendación comercial según resultado
        if predicted_class == ">50K":
            recommendation = "Califica para producto de crédito de alto monto (Perfil Solvente con ingresos superiores a $50K USD)."
        else:
            recommendation = "No califica para producto de crédito de alto monto (Riesgo crediticio elevado o ingresos inferiores al umbral)."

        # Persistir auditoría en base de datos si la sesión está disponible
        prediction_id = None
        if db is not None:
            try:
                db_record = Prediction(
                    model_version=self.model_version,
                    input_data=data_dict,
                    predicted_class=predicted_class,
                    probability=round(probability, 4),
                    latency_ms=latency_ms,
                )
                db.add(db_record)
                db.commit()
                db.refresh(db_record)
                prediction_id = db_record.id
                logger.info(f"Predicción registrada en DB con ID: {prediction_id} (Clase: {predicted_class}, P={probability:.4f})")
            except Exception as e:
                db.rollback()
                logger.error(f"Error al persistir auditoría de predicción en DB: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Fallo al persistir la auditoría de predicción en la base de datos: {str(e)}",
                )

        return PredictionResponse(
            predicted_class=predicted_class,
            probability=round(probability, 4),
            threshold_applied=round(self.threshold, 4),
            latency_ms=latency_ms,
            model_version=self.model_version,
            recommendation=recommendation,
            prediction_id=prediction_id,
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna las métricas y configuración del modelo activo."""
        if not self.metadata:
            self.load_active_model(raise_on_missing=False)
        if not self.metadata:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Los metadatos del modelo no están disponibles. Se requiere entrenar un modelo primero.",
            )
        return self.metadata


ml_service = MLService()
