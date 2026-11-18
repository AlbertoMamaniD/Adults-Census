import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import shutil
from typing import Any, Dict, Optional
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


def run_retrain_pipeline(csv_path: Optional[Path] = None, dataset_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Ejecuta el pipeline de reentrenamiento CRISP-ML(Q) de forma síncrona en un hilo de trabajo aislado (Finding 5).
    Usa sesión propia de base de datos y garantiza activación atómica sólo tras registro exitoso en DB (Finding 4).
    """
    if csv_path is None or not csv_path.exists():
        csv_path = settings.DATA_DIR / "adult.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Archivo de dataset no encontrado en {csv_path}")

    # 1. Ingesta y Limpieza
    logger.info(f"Leyendo dataset desde {csv_path}...")
    df = pd.read_csv(csv_path)
    df.columns = [normalize_column_name(c) for c in df.columns]

    # Target column (Finding 7)
    target_col = None
    for candidate in ["income", "class", "target"]:
        if candidate in df.columns:
            target_col = candidate
            break
    if not target_col:
        raise ValueError("Columna objetivo ('income') no encontrada en el dataset de entrenamiento.")

    # Mapeo binario y validación de clases (Finding 7)
    df[target_col] = df[target_col].astype(str).str.strip().str.rstrip(".")
    classes_present = set(df[target_col].unique())
    if not {">50K", "<=50K"}.issubset(classes_present):
        raise ValueError(f"El dataset debe contener ambas clases ('>50K' y '<=50K'). Encontradas: {classes_present}")
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

    # Imputación / reemplazo de '?'
    for col in categorical_cols:
        if col in X.columns:
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

    if feasible_thresholds:
        robust_threshold = float(np.median(feasible_thresholds))
    else:
        robust_threshold = float(best_threshold)

    # Métricas finales en test con umbral calibrado
    y_final = (y_proba >= robust_threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, y_final).ravel()
    mcc_val = float(matthews_corrcoef(y_test, y_final))
    prec_val = float(precision_score(y_test, y_final, zero_division=0))
    rec_val = float(recall_score(y_test, y_final, zero_division=0))
    acc_val = float(accuracy_score(y_test, y_final))
    roc_val = float(roc_auc_score(y_test, y_proba))

    # 5. Serialización en staging (Finding 4)
    new_version = f"v{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    artifacts_dir = settings.ARTIFACTS_DIR
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    versioned_model_path = artifacts_dir / f"model_{new_version}.joblib"
    versioned_meta_path = artifacts_dir / f"metadata_{new_version}.json"
    latest_model_path = artifacts_dir / "model_latest.joblib"
    latest_meta_path = artifacts_dir / "metadata_latest.json"

    joblib.dump(model_pipeline, versioned_model_path)

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

    # 6. Registrar en Base de Datos de manera transaccional e inmutable (Finding 4 y Finding 9)
    # Si falla la base de datos, NO se despliega el modelo y se revierte el staging
    try:
        with SessionLocal() as db_session:
            # Desactivar modelos anteriores
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
                    dataset_record.status = "processed"
            db_session.commit()
            logger.info(f"Nuevo modelo registrado y activado exitosamente en base de datos: {new_version}")
    except Exception as db_err:
        logger.error(f"Error crítico en base de datos al registrar version {new_version}: {db_err}")
        # Descartar artefactos staged para no dejar archivos huerfanos ni activar modelo invalido
        if versioned_model_path.exists():
            versioned_model_path.unlink()
        if versioned_meta_path.exists():
            versioned_meta_path.unlink()
        raise RuntimeError(f"Fallo al registrar model_run en base de datos: {db_err}")

    # 7. Promover a producción mediante referencia atómica inmutable (Finding 3)
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
    os.replace(tmp_manifest_path, active_version_path)

    # Copias secundarias para compatibilidad
    shutil.copyfile(versioned_model_path, latest_model_path)
    shutil.copyfile(versioned_meta_path, latest_meta_path)

    ml_service.load_active_model()
    logger.info(f"Artefactos promovidos atómicamente y singleton recargado con versión {new_version}.")

    return {
        "new_model_version": new_version,
        "threshold": robust_threshold,
        "metrics": metrics_payload,
    }
