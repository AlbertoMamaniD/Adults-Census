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
from app.database.models import ModelRun, Prediction
from app.schemas.prediction import PredictionInput, PredictionResponse

logger = logging.getLogger("ml_service")


class MLService:
    """Servicio singleton para inferencia, gestión de modelo en memoria y auditoría."""

    def __init__(self) -> None:
        self.model: Optional[Any] = None
        self.metadata: Dict[str, Any] = {}
        self.model_version: str = "unknown"
        self.threshold: float = 0.77
        self.is_fallback: bool = False
        self.requested_version: Optional[str] = None
        self.load_active_model(raise_on_missing=False)

    def load_active_model(self, target_version: Optional[str] = None, raise_on_missing: bool = False) -> None:
        """Carga en memoria el artefacto binario y los metadatos desde el par atómico inmutable o versión objetivo."""
        self.requested_version = target_version
        self.is_fallback = False
        active_version_file = settings.ARTIFACTS_DIR / "active_version.json"
        model_path = None
        metadata_path = None

        # 1. Si se solicita una versión objetivo (ej. activa en DB), verificar si existe físicamente en disco
        if target_version:
            m_cand = settings.ARTIFACTS_DIR / f"model_{target_version}.joblib"
            meta_cand = settings.ARTIFACTS_DIR / f"metadata_{target_version}.json"
            if m_cand.exists() and meta_cand.exists():
                model_path = m_cand
                metadata_path = meta_cand
                logger.info(f"Cargando versión activa objetivo desde disco: {target_version}")
            else:
                self.is_fallback = True
                logger.warning(
                    f"Versión solicitada '{target_version}' no encontrada en disco local. "
                    "Activando modo degradado de respaldo (fallback) sin sobrescribir la versión activa de la base de datos."
                )

        # 2. Si no, consultar el manifiesto atómico active_version.json
        if model_path is None and active_version_file.exists():
            try:
                with open(active_version_file, "r", encoding="utf-8") as f:
                    v_data = json.load(f)
                v = v_data.get("model_version")
                m_cand = settings.ARTIFACTS_DIR / v_data.get("model_file", f"model_{v}.joblib")
                meta_cand = settings.ARTIFACTS_DIR / v_data.get("metadata_file", f"metadata_{v}.json")
                if m_cand.exists() and meta_cand.exists():
                    model_path = m_cand
                    metadata_path = meta_cand
                    logger.info(f"Cargando versión activa atómica: {v}")
            except Exception as err:
                logger.warning(f"Aviso al consultar active_version.json: {err}")

        if model_path is None or metadata_path is None:
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
            if target_version and self.model_version != target_version:
                self.is_fallback = True
            logger.info(
                f"Metadatos cargados con éxito. Versión: {self.model_version}, Umbral Calibrado: {self.threshold:.4f} "
                f"(Fallback: {self.is_fallback})"
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
            # 1. Asegurar registro de ModelRun ante recuperación post-caída de BD (Finding 4)
            try:
                run_exists = db.query(ModelRun).filter(ModelRun.model_version == self.model_version).first()
                if not run_exists:
                    logger.info(f"Auto-recuperando registro de model_version '{self.model_version}' en base de datos...")
                    raw_m = self.metadata.get("metrics", {})
                    cm = raw_m.get("confusion_matrix", {})
                    tn = cm.get("tn") if "tn" in cm else raw_m.get("true_negatives", 0)
                    fp = cm.get("fp") if "fp" in cm else raw_m.get("false_positives", 0)
                    fn = cm.get("fn") if "fn" in cm else raw_m.get("false_negatives", 0)
                    tp = cm.get("tp") if "tp" in cm else raw_m.get("true_positives", 0)
                    normalized_metrics = {
                        **raw_m,
                        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
                    }
                    new_run = ModelRun(
                        model_version=self.model_version,
                        model_name=self.metadata.get("model_name", "Gradient boosting"),
                        threshold=self.threshold,
                        metrics=normalized_metrics,
                        parameters=self.metadata.get("parameters", {}),
                        is_active=True,
                    )
                    db.add(new_run)
                    db.commit()
            except Exception as auto_rec_err:
                db.rollback()
                logger.warning(f"Aviso en verificación/auto-recuperación de ModelRun: {auto_rec_err}")

            # 2. Persistir predicción
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
