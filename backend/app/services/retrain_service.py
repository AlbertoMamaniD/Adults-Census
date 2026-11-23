import asyncio
import contextlib
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import shutil
import threading
from typing import Any, Dict, Optional
import uuid
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy import text
from app.config import settings
from app.database.connection import SessionLocal
from app.database.models import ModelRun, TrainingDataset
from app.services.ml_service import ml_service
from app.services.websocket_manager import ws_manager

logger = logging.getLogger("retrain_service")


def normalize_column_name(col: str) -> str:
    """Normaliza nombres de columnas censales admitiendo guiones y puntos (Finding 2)."""
    return col.strip().lower().replace("-", "_").replace(".", "_")


async def emit_progress(stage: str, progress: int, message: str, payload: Optional[Dict[str, Any]] = None):
    """Emite un evento de progreso tanto por logs como por WebSocket."""
    logger.info(f"[{stage.upper()}] ({progress}%): {message}")
    event = {
        "stage": stage,
        "progress": progress,
        "message": message,
        "payload": payload or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await ws_manager.broadcast(event)


# Bloqueo global de concurrencia para reentrenamiento (Qodo Finding 6)
_retrain_pipeline_lock = threading.Lock()
MAX_CATEGORICAL_CARDINALITY = 100


@contextlib.contextmanager
def cross_process_publish_lock(artifacts_dir: Path):
    """Bloqueo a nivel de proceso (cross-process) para coordinar la publicación atómica entre workers (Qodo Finding 2)."""
    lock_file = artifacts_dir / ".publish.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    f = open(lock_file, "a+")
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            f.close()
        except Exception:
            pass


def run_retrain_pipeline(csv_path: Optional[Path] = None, dataset_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Ejecuta el pipeline de reentrenamiento CRISP-ML(Q) de forma síncrona en un hilo de trabajo aislado.
    Implementa control de concurrencia, límites de cardinalidad, compuerta de calidad y publicación atómica (Qodo Findings 1, 3, 5, 6).
    """
    acquired = _retrain_pipeline_lock.acquire(blocking=False)
    if not acquired:
        raise RuntimeError("Ya existe un proceso de reentrenamiento ejecutándose concurrentemente.")

    training_started_at = datetime.now(timezone.utc)
    try:
        if csv_path is None or not csv_path.exists():
            csv_path = settings.DATA_DIR / "adult.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"Archivo de dataset no encontrado en {csv_path}")

        # 1. Ingesta y Limpieza
        logger.info(f"Leyendo dataset desde {csv_path}...")
        df = pd.read_csv(csv_path)
        df.columns = [normalize_column_name(c) for c in df.columns]

        # Target column
        target_col = None
        for candidate in ["income", "class", "target"]:
            if candidate in df.columns:
                target_col = candidate
                break
        if not target_col:
            raise ValueError("Columna objetivo ('income') no encontrada en el dataset de entrenamiento.")

        # Mapeo binario y validación estricta de clases (Qodo Finding 5)
        df[target_col] = df[target_col].astype(str).str.strip().str.rstrip(".")
        classes_present = set(df[target_col].unique())
        unexpected_classes = classes_present - {">50K", "<=50K"}
        if unexpected_classes or classes_present != {">50K", "<=50K"}:
            raise ValueError(
                f"El dataset contiene etiquetas no permitidas o incompletas en '{target_col}': {sorted(list(classes_present))}. "
                "Solo se permiten exclusivamente las clases '>50K' y '<=50K'."
            )
        counts = df[target_col].value_counts()
        if counts.get(">50K", 0) < 5 or counts.get("<=50K", 0) < 5:
            raise ValueError("Cada clase en el dataset debe contener al menos 5 ejemplos representativos para validación estratificada.")

        y = (df[target_col] == ">50K").astype(int)
        X = df.drop(columns=[target_col])

        # Filtrar columnas no predictivas si existen (fnlwgt, education redundante con education_num)
        for col_to_drop in ["fnlwgt", "education"]:
            if col_to_drop in X.columns:
                X = X.drop(columns=[col_to_drop])

        numeric_cols = ["age", "education_num", "capital_gain", "capital_loss", "hours_per_week"]
        categorical_cols = ["workclass", "marital_status", "occupation", "relationship", "race", "sex", "native_country"]

        # Validar y acotar cardinalidad categórica para proteger la memoria de OneHotEncoder (Qodo Finding 1)
        for col in categorical_cols:
            if col in X.columns:
                cardinality = X[col].nunique()
                if cardinality > MAX_CATEGORICAL_CARDINALITY:
                    raise ValueError(
                        f"La columna categórica '{col}' supera la cardinalidad máxima permitida ({MAX_CATEGORICAL_CARDINALITY}). "
                        f"Detectados: {cardinality}."
                    )
                X[col] = X[col].astype(str).str.strip().replace("?", "Unknown")

        for col in numeric_cols:
            if col in X.columns:
                X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

        # 2. División estratificada
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=42, stratify=y
        )

        # 3. Preprocesamiento y Modelo
        preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), [c for c in numeric_cols if c in X.columns]),
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), [c for c in categorical_cols if c in X.columns]),
            ]
        )

        model_pipeline = Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("classifier", HistGradientBoostingClassifier(random_state=42, max_iter=150, learning_rate=0.1)),
            ]
        )

        model_pipeline.fit(X_train, y_train)

        # 4. Evaluación y Calibración de Umbral
        y_proba = model_pipeline.predict_proba(X_test)[:, 1]
        
        # Búsqueda de umbral robusto mediano que satisfaga Precision >= 0.75 y Recall >= 0.60
        feasible_thresholds = []
        best_threshold = 0.77
        min_cost = float("inf")
        
        for t in np.linspace(0.40, 0.85, 46):
            y_pred = (y_proba >= t).astype(int)
            p = precision_score(y_test, y_pred, zero_division=0)
            r = recall_score(y_test, y_pred, zero_division=0)
            tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
            cost = 3.0 * fp + 1.0 * fn
            if p >= 0.75 and r >= 0.60:
                feasible_thresholds.append(round(t, 2))
                if cost < min_cost:
                    min_cost = cost
                    best_threshold = round(t, 2)

        # Seleccionar estrictamente el umbral óptimo que minimiza el costo asimétrico C = 3*FP + 1*FN (Qodo Finding 6)
        robust_threshold = float(best_threshold)

        # Métricas finales en test con umbral calibrado
        y_final = (y_proba >= robust_threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, y_final).ravel()
        mcc_val = float(matthews_corrcoef(y_test, y_final))
        prec_val = float(precision_score(y_test, y_final, zero_division=0))
        rec_val = float(recall_score(y_test, y_final, zero_division=0))
        acc_val = float(accuracy_score(y_test, y_final))
        roc_val = float(roc_auc_score(y_test, y_proba))

        # ID de versión único resistente a colisiones concurrentes (Qodo Finding 6)
        new_version = f"v{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
        artifacts_dir = settings.ARTIFACTS_DIR
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        versioned_model_path = artifacts_dir / f"model_{new_version}.joblib"
        versioned_meta_path = artifacts_dir / f"metadata_{new_version}.json"
        latest_model_path = artifacts_dir / "model_latest.joblib"
        latest_meta_path = artifacts_dir / "metadata_latest.json"

        metrics_payload = {
            "threshold": robust_threshold,
            "mcc": round(mcc_val, 4),
            "precision": round(prec_val, 4),
            "recall": round(rec_val, 4),
            "roc_auc": round(roc_val, 4),
            "accuracy": round(acc_val, 4),
            "confusion_matrix": {
                "tn": int(tn),
                "fp": int(fp),
                "fn": int(fn),
                "tp": int(tp),
            },
            "expected_cost": float(3.0 * fp + 1.0 * fn),
        }

        # Control de calidad CRISP-ML(Q) obligatorio (Qodo Finding 3):
        # Exigir que existan umbrales factibles y que el MCC >= 0.50 y ROC-AUC >= 0.85
        quality_passed = bool(feasible_thresholds and mcc_val >= 0.50 and roc_val >= 0.85)

        if not quality_passed:
            logger.warning(
                f"El modelo candidato '{new_version}' no superó las metas mínimas de calidad CRISP-ML(Q) "
                f"(MCC: {mcc_val:.4f}, Feasible Thresholds: {len(feasible_thresholds)}, ROC-AUC: {roc_val:.4f}). "
                "No se promoverá a producción para preservar la estabilidad del scoring."
            )
            try:
                with SessionLocal() as db_session:
                    rejected_run = ModelRun(
                        model_version=new_version,
                        model_name="HistGradientBoostingClassifier",
                        threshold=robust_threshold,
                        metrics=metrics_payload,
                        parameters={"max_iter": 150, "learning_rate": 0.1, "random_state": 42},
                        is_active=False,
                    )
                    db_session.add(rejected_run)
                    if dataset_id is not None:
                        dataset_record = db_session.query(TrainingDataset).filter(TrainingDataset.id == dataset_id).first()
                        if dataset_record:
                            dataset_record.status = "processed"
                    db_session.commit()
            except Exception as db_err:
                logger.warning(f"Aviso registrando candidato rechazado en base de datos: {db_err}")

            return {
                "status": "rejected",
                "message": (
                    f"Reentrenamiento completado pero el modelo candidato '{new_version}' fue RECHAZADO por no superar "
                    f"las metas de calidad mínimas (MCC={mcc_val:.4f} < 0.50 o sin umbral factible). "
                    f"El modelo de producción activo ({ml_service.model_version}) se mantiene sin cambios."
                ),
                "new_model_version": ml_service.model_version,
                "candidate_version": new_version,
                "threshold": ml_service.threshold,
                "metrics": metrics_payload,
            }

        # 5. Serialización en staging si superó las metas de calidad
        joblib.dump(model_pipeline, versioned_model_path)

        metadata = {
            "model_version": new_version,
            "model_name": "Gradient boosting (HistGradientBoostingClassifier)",
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "threshold": robust_threshold,
            "positive_label": ">50K",
            "negative_label": "<=50K",
            "numeric_columns": [c for c in numeric_cols if c in X.columns],
            "categorical_columns": [c for c in categorical_cols if c in X.columns],
            "metrics": metrics_payload,
            "parameters": {"max_iter": 150, "learning_rate": 0.1, "random_state": 42},
            "sklearn_version": "1.9.1",
            "random_state": 42,
            "cost_fp": 3.0,
            "cost_fn": 1.0,
        }

        with open(versioned_meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # 6 y 7. Publicación atómica coordinada con protección ante fallos y bloqueo entre procesos (Qodo Finding 1 y 2)
        # Se asegura que ante cualquier fallo antes o durante el commit en base de datos,
        # los archivos previos sean íntegramente restaurados y el modelo previo explícitamente recargado en memoria.
        with cross_process_publish_lock(artifacts_dir):
            active_manifest = {
                "model_version": new_version,
                "model_file": f"model_{new_version}.joblib",
                "metadata_file": f"metadata_{new_version}.json",
                "threshold": robust_threshold,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
            tmp_manifest_path = artifacts_dir / f"active_version_{new_version}.tmp"
            with open(tmp_manifest_path, "w", encoding="utf-8") as f:
                json.dump(active_manifest, f, indent=2)

            active_version_path = artifacts_dir / "active_version.json"

            # 1. Preservar manifiesto y artefactos de compatibilidad previos en memoria antes de cualquier reemplazo (Qodo Finding 1)
            old_manifest_bytes: Optional[bytes] = active_version_path.read_bytes() if active_version_path.exists() else None
            old_model_latest_bytes: Optional[bytes] = latest_model_path.read_bytes() if latest_model_path.exists() else None
            old_meta_latest_bytes: Optional[bytes] = latest_meta_path.read_bytes() if latest_meta_path.exists() else None

            # Obtener la versión actualmente activa para poder restaurarla de manera determinista ante fallos
            with SessionLocal() as check_session:
                prev_run = check_session.query(ModelRun).filter(ModelRun.is_active == True).order_by(ModelRun.id.desc()).first()
                previous_active_version = prev_run.model_version if prev_run else ml_service.model_version

                # Protocolo de promoción: verificar únicamente contra modelos activados exitosamente (Qodo Finding 1)
                latest_active_run = check_session.query(ModelRun).filter(ModelRun.is_active == True).order_by(ModelRun.id.desc()).first()
                if latest_active_run and latest_active_run.created_at:
                    created_at_utc = latest_active_run.created_at.replace(tzinfo=timezone.utc) if latest_active_run.created_at.tzinfo is None else latest_active_run.created_at
                    if created_at_utc > training_started_at:
                        logger.warning(
                            f"Existe una versión activa más reciente ({latest_active_run.model_version}) "
                            f"activada en {created_at_utc}. Abortando promoción de {new_version}."
                        )
                        if tmp_manifest_path.exists():
                            tmp_manifest_path.unlink()
                        return {
                            "status": "superseded",
                            "message": f"El modelo candidato '{new_version}' fue superado por una versión más reciente activa ({latest_active_run.model_version}).",
                            "new_model_version": latest_active_run.model_version,
                            "threshold": latest_active_run.threshold,
                            "metrics": latest_active_run.metrics or metrics_payload,
                        }

            db_committed = False
            prior_dataset_status: Optional[str] = None
            try:
                # 2. Registrar y confirmar primero en Base de Datos de manera transaccional (Qodo Finding 1 y 2)
                with SessionLocal() as db_session:
                    if db_session.bind.dialect.name == "postgresql":
                        db_session.execute(text("SELECT pg_advisory_xact_lock(742198)"))

                    db_session.query(ModelRun).filter(ModelRun.is_active == True).update({"is_active": False})
                    new_run = ModelRun(
                        model_version=new_version,
                        model_name=metadata["model_name"],
                        threshold=robust_threshold,
                        metrics=metrics_payload,
                        parameters=metadata["parameters"],
                        is_active=True,
                    )
                    db_session.add(new_run)
                    if dataset_id is not None:
                        dataset_record = db_session.query(TrainingDataset).filter(TrainingDataset.id == dataset_id).first()
                        if dataset_record:
                            prior_dataset_status = dataset_record.status  # Capturar estado previo del lote (Qodo Finding 2)
                            dataset_record.status = "processed"
                    db_session.commit()
                    db_committed = True
                    logger.info(f"Nuevo modelo registrado y activado exitosamente en base de datos: {new_version}")

                # 3. Solo tras el commit exitoso en base de datos, reemplazar manifiesto y artefactos en disco
                os.replace(tmp_manifest_path, active_version_path)
                shutil.copyfile(versioned_model_path, latest_model_path)
                shutil.copyfile(versioned_meta_path, latest_meta_path)

                # 4. Recargar el modelo en memoria con la versión recién confirmada
                ml_service.load_active_model(target_version=new_version, raise_on_missing=True)

            except Exception as pub_err:
                logger.error(f"Error durante la publicación de la versión {new_version}: {pub_err}")
                if tmp_manifest_path.exists():
                    try:
                        tmp_manifest_path.unlink()
                    except Exception:
                        pass

                # Purgar archivos de artefactos candidatos no confirmados para no dejar basura en disco
                for cand_file in [versioned_model_path, versioned_meta_path]:
                    if cand_file.exists():
                        try:
                            cand_file.unlink()
                        except Exception:
                            pass

                # Si falló la publicación en disco después de haber hecho commit en DB, compensar en base de datos
                compensation_failed = False
                if db_committed:
                    try:
                        with SessionLocal() as comp_session:
                            comp_session.query(ModelRun).filter(ModelRun.model_version == new_version).update({"is_active": False})
                            if previous_active_version:
                                comp_session.query(ModelRun).filter(ModelRun.model_version == previous_active_version).update({"is_active": True})
                            # Restaurar el estado previo del dataset si fue procesado (Qodo Finding 2)
                            if dataset_id is not None and prior_dataset_status is not None:
                                comp_ds = comp_session.query(TrainingDataset).filter(TrainingDataset.id == dataset_id).first()
                                if comp_ds:
                                    comp_ds.status = prior_dataset_status
                            comp_session.commit()
                            logger.info(f"Compensación ejecutada: versión {new_version} desactivada, restaurada {previous_active_version} y dataset #{dataset_id} restaurado a '{prior_dataset_status}'")
                    except Exception as comp_err:
                        compensation_failed = True
                        logger.critical(f"Fallo crítico en compensación de base de datos tras error de publicación: {comp_err}")

                # Tratar compensación fallida como estado no resuelto: no fingir rollback exitoso (Qodo Finding 3)
                if compensation_failed:
                    ml_service.is_fallback = True
                    raise RuntimeError(
                        f"Fallo crítico irresoluble: falló la compensación en base de datos para la versión {new_version}. "
                        "Servicio puesto en modo degradado para evitar división de estado entre inferencia y base de datos."
                    )

                # Restaurar manifiesto y artefactos de compatibilidad previos a su estado exacto (Qodo Finding 4)
                if old_manifest_bytes is not None:
                    active_version_path.write_bytes(old_manifest_bytes)
                elif active_version_path.exists():
                    try:
                        active_version_path.unlink()
                    except Exception:
                        pass

                if old_model_latest_bytes is not None:
                    latest_model_path.write_bytes(old_model_latest_bytes)
                elif latest_model_path.exists():
                    try:
                        latest_model_path.unlink()
                    except Exception:
                        pass

                if old_meta_latest_bytes is not None:
                    latest_meta_path.write_bytes(old_meta_latest_bytes)
                elif latest_meta_path.exists():
                    try:
                        latest_meta_path.unlink()
                    except Exception:
                        pass

                # Recargar explícitamente la versión previamente activa solo tras completar la restauración íntegra de archivos
                ml_service.load_active_model(target_version=previous_active_version)
                raise RuntimeError(f"Fallo al publicar y registrar modelo en producción: {pub_err}")

        return {
            "status": "success",
            "new_model_version": new_version,
            "threshold": robust_threshold,
            "metrics": metrics_payload,
        }
    finally:
        _retrain_pipeline_lock.release()
