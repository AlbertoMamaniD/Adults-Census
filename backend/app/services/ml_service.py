from dataclasses import dataclass
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, status
import joblib
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.database.models import ModelRun, Prediction
from app.schemas.prediction import PredictionInput, PredictionResponse

logger = logging.getLogger("ml_service")


@dataclass(frozen=True)
class ModelSnapshot:
    """Instantánea inmutable de modelo y metadatos para inferencia atómica (Qodo Finding 13)."""
    model: Any
    metadata: Dict[str, Any]
    model_version: str
    threshold: float
    is_fallback: bool


class MLService:
    """Servicio singleton para inferencia, gestión de modelo en memoria y auditoría."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot: Optional[ModelSnapshot] = None
        self.requested_version: Optional[str] = None
        self.load_active_model(raise_on_missing=False)

    @property
    def model(self) -> Optional[Any]:
        return self._snapshot.model if self._snapshot else None

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._snapshot.metadata if self._snapshot else {}

    @property
    def model_version(self) -> str:
        return self._snapshot.model_version if self._snapshot else "unknown"

    @model_version.setter
    def model_version(self, value: str) -> None:
        with self._lock:
            if self._snapshot:
                self._snapshot = ModelSnapshot(
                    model=self._snapshot.model,
                    metadata=self._snapshot.metadata,
                    model_version=value,
                    threshold=self._snapshot.threshold,
                    is_fallback=self._snapshot.is_fallback,
                )

    @property
    def threshold(self) -> float:
        return self._snapshot.threshold if self._snapshot else 0.77

    @property
    def is_fallback(self) -> bool:
        return self._snapshot.is_fallback if self._snapshot else False

    @is_fallback.setter
    def is_fallback(self, value: bool) -> None:
        with self._lock:
            if self._snapshot:
                self._snapshot = ModelSnapshot(
                    model=self._snapshot.model,
                    metadata=self._snapshot.metadata,
                    model_version=self._snapshot.model_version,
                    threshold=self._snapshot.threshold,
                    is_fallback=value,
                )

    def load_active_model(self, target_version: Optional[str] = None, raise_on_missing: bool = False) -> None:
        """Carga en memoria el artefacto binario y los metadatos desde un par atómico inmutable verificado (Qodo Finding 10)."""
        self.requested_version = target_version
        active_version_file = settings.ARTIFACTS_DIR / "active_version.json"

        def _try_load_pair(m_cand: Path, meta_cand: Path) -> Optional[Tuple[Any, Dict[str, Any]]]:
            # Ambos archivos deben existir simultáneamente como un par íntegro verificado
            if not m_cand.exists() or not meta_cand.exists():
                return None
            try:
                mod = joblib.load(m_cand)
                with open(meta_cand, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                return mod, meta
            except Exception as err:
                logger.warning(f"Error al verificar/cargar par de artefactos ({m_cand.name}, {meta_cand.name}): {err}")
                return None

        loaded_pair = None
        is_fallback = False

        # 1. Si se solicita una versión objetivo (ej. activa en DB), verificar si existe físicamente en disco
        if target_version:
            m_cand = settings.ARTIFACTS_DIR / f"model_{target_version}.joblib"
            meta_cand = settings.ARTIFACTS_DIR / f"metadata_{target_version}.json"
            loaded_pair = _try_load_pair(m_cand, meta_cand)
            if loaded_pair:
                logger.info(f"Cargando versión activa objetivo desde disco: {target_version}")
            else:
                is_fallback = True
                logger.warning(
                    f"Versión solicitada '{target_version}' no encontrada o par incompleto en disco. "
                    "Activando modo degradado de respaldo (fallback) sin sobrescribir la versión activa de la base de datos."
                )

        # 2. Si no, consultar el manifiesto atómico active_version.json
        if loaded_pair is None and active_version_file.exists():
            try:
                with open(active_version_file, "r", encoding="utf-8") as f:
                    v_data = json.load(f)
                v = v_data.get("model_version")
                m_cand = settings.ARTIFACTS_DIR / v_data.get("model_file", f"model_{v}.joblib")
                meta_cand = settings.ARTIFACTS_DIR / v_data.get("metadata_file", f"metadata_{v}.json")
                loaded_pair = _try_load_pair(m_cand, meta_cand)
                if loaded_pair:
                    logger.info(f"Cargando versión activa atómica: {v}")
            except Exception as err:
                logger.warning(f"Aviso al consultar active_version.json: {err}")

        # 3. Fallback a artefactos genéricos latest si el par es completo y válido
        if loaded_pair is None:
            latest_m = settings.ARTIFACTS_DIR / "model_latest.joblib"
            latest_meta = settings.ARTIFACTS_DIR / "metadata_latest.json"
            loaded_pair = _try_load_pair(latest_m, latest_meta)
            if loaded_pair and target_version:
                is_fallback = True

        if loaded_pair is None:
            logger.warning("No se encontró ningún par completo y verificado de modelo y metadatos. Servicio en espera.")
            if raise_on_missing:
                raise FileNotFoundError("No se encontró un par verificado de modelo (.joblib) y metadatos (.json).")
            with self._lock:
                self._snapshot = None
            return

        loaded_model, loaded_meta = loaded_pair
        version = loaded_meta.get("model_version", "unknown")
        threshold = float(loaded_meta.get("threshold", 0.77))
        if target_version and version != target_version:
            is_fallback = True

        new_snapshot = ModelSnapshot(
            model=loaded_model,
            metadata=loaded_meta,
            model_version=version,
            threshold=threshold,
            is_fallback=is_fallback,
        )

        with self._lock:
            self._snapshot = new_snapshot

        logger.info(
            f"Metadatos y modelo publicados atómicamente. Versión: {version}, Umbral Calibrado: {threshold:.4f} "
            f"(Fallback: {is_fallback})"
        )

    def predict(self, input_data: PredictionInput, db: Optional[Session] = None) -> PredictionResponse:
        """Ejecuta inferencia en tiempo real leyendo una instantánea inmutable consistente (Qodo Finding 13)."""
        snapshot = self._snapshot
        if snapshot is None or snapshot.model is None:
            self.load_active_model(raise_on_missing=False)
            snapshot = self._snapshot
            if snapshot is None or snapshot.model is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="El modelo de inferencia no está disponible en este momento. Por favor ejecute el reentrenamiento para inicializarlo.",
                )

        data_dict = input_data.to_inference_dict()
        df = pd.DataFrame([data_dict])

        # Medición rigurosa de latencia usando la instantánea inmutable
        start_time = time.perf_counter()
        proba_matrix = snapshot.model.predict_proba(df)
        end_time = time.perf_counter()
        latency_ms = round((end_time - start_time) * 1000, 2)

        # Probabilidad de clase positiva (>50K)
        probability = float(proba_matrix[0, 1])
        predicted_class = ">50K" if probability >= snapshot.threshold else "<=50K"

        # Recomendación comercial según resultado
        if predicted_class == ">50K":
            recommendation = "Califica para producto de crédito de alto monto (Perfil Solvente con ingresos superiores a $50K USD)."
        else:
            recommendation = "No califica para producto de crédito de alto monto (Riesgo crediticio elevado o ingresos inferiores al umbral)."

        # Persistir auditoría en base de datos si la sesión está disponible
        prediction_id = None
        if db is not None:
            # 1. Asegurar registro de ModelRun ante recuperación post-caída de BD (Qodo Findings 1 y 2)
            try:
                run_exists = db.query(ModelRun).filter(ModelRun.model_version == snapshot.model_version).first()
                if not run_exists:
                    logger.info(f"Auto-recuperando registro de model_version '{snapshot.model_version}' en base de datos...")
                    raw_m = snapshot.metadata.get("metrics", {})
                    cm = raw_m.get("confusion_matrix", {})
                    tn = cm.get("tn") if "tn" in cm else raw_m.get("true_negatives", 0)
                    fp = cm.get("fp") if "fp" in cm else raw_m.get("false_positives", 0)
                    fn = cm.get("fn") if "fn" in cm else raw_m.get("false_negatives", 0)
                    tp = cm.get("tp") if "tp" in cm else raw_m.get("true_positives", 0)
                    normalized_metrics = {
                        **raw_m,
                        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
                    }

                    # Serializar la recuperación contra otras transiciones de modelo activo en BD
                    if db.bind.dialect.name == "postgresql":
                        db.execute(text("SELECT pg_advisory_xact_lock(742198)"))

                    is_active_for_recovery = False
                    if not snapshot.is_fallback:
                        active_exists = db.query(ModelRun).filter(ModelRun.is_active == True).first()
                        if not active_exists or active_exists.model_version == snapshot.model_version:
                            is_active_for_recovery = True

                    try:
                        with db.begin_nested():
                            new_run = ModelRun(
                                model_version=snapshot.model_version,
                                model_name=snapshot.metadata.get("model_name", "HistGradientBoostingClassifier"),
                                threshold=snapshot.threshold,
                                metrics=normalized_metrics,
                                parameters=snapshot.metadata.get("parameters", {}),
                                is_active=is_active_for_recovery,
                            )
                            db.add(new_run)
                            db.flush()
                        db.commit()
                    except IntegrityError:
                        db.rollback()
                        logger.warning(
                            f"Conflicto de modelo activo único al registrar '{snapshot.model_version}'. "
                            "Reintentando registro como inactivo para preservar el modelo activo vigente..."
                        )
                        run_after_rollback = db.query(ModelRun).filter(ModelRun.model_version == snapshot.model_version).first()
                        if not run_after_rollback:
                            fallback_run = ModelRun(
                                model_version=snapshot.model_version,
                                model_name=snapshot.metadata.get("model_name", "HistGradientBoostingClassifier"),
                                threshold=snapshot.threshold,
                                metrics=normalized_metrics,
                                parameters=snapshot.metadata.get("parameters", {}),
                                is_active=False,
                            )
                            db.add(fallback_run)
                            db.commit()
            except Exception as auto_rec_err:
                db.rollback()
                logger.warning(f"Aviso en verificación/auto-recuperación de ModelRun: {auto_rec_err}")

            # 2. Persistir predicción
            try:
                db_record = Prediction(
                    model_version=snapshot.model_version,
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
            threshold_applied=round(snapshot.threshold, 4),
            latency_ms=latency_ms,
            model_version=snapshot.model_version,
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
