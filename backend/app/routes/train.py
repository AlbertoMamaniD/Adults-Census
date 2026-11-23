import asyncio
import logging
from pathlib import Path
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
import pandas as pd
from sqlalchemy.orm import Session
from app.config import settings
from app.database.connection import get_db
from app.database.models import TrainingDataset
from app.schemas.training import RetrainRequest, RetrainResponse, UploadDatasetResponse
from app.services.auth_service import get_current_user
from app.services.retrain_service import emit_progress, normalize_column_name, run_retrain_pipeline

router = APIRouter(prefix="", tags=["Entrenamiento y MLOps"])
logger = logging.getLogger("train_routes")

# Bloqueo concurrente de reentrenamiento
_is_retraining_lock = asyncio.Lock()
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB límite
CHUNK_SIZE_BYTES = 1024 * 1024          # 1 MB por chunk de lectura (Finding 11)


@router.post(
    "/train/upload",
    response_model=UploadDatasetResponse,
    status_code=status.HTTP_200_OK,
    summary="Cargar nuevo dataset para reentrenamiento (Autenticado)",
    description=(
        "Sube un archivo CSV con datos censales en streaming por bloques, valida columnas obligatorias "
        "(tolerando nombres con puntos y guiones), verifica la variable objetivo ('income') y el balance de clases, "
        "y registra el lote en la base de datos."
    ),
    responses={
        200: {"description": "Dataset validado y registrado exitosamente."},
        400: {"description": "Error en formato de archivo, columnas faltantes o datos insuficientes."},
        401: {"description": "No autorizado. Token Bearer ausente o inválido."},
        413: {"description": "Archivo excede el límite de 50 MB."},
    },
)
async def upload_training_dataset(
    file: UploadFile = File(..., description="Archivo CSV del dataset de entrenamiento"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato inválido. Solo se admiten archivos con extensión .csv.",
        )

    data_dir = settings.DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    safe_basename = Path(file.filename).name.replace(" ", "_")
    storage_filename = f"upload_{uuid.uuid4().hex[:12]}_{safe_basename}"
    destination_path = data_dir / storage_filename

    # Lectura en chunks delimitados para proteger memoria RAM (Finding 11)
    file_size = 0
    try:
        with open(destination_path, "wb") as f_out:
            while True:
                chunk = await file.read(CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE_BYTES:
                    f_out.close()
                    if destination_path.exists():
                        destination_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"El archivo excede el tamaño máximo permitido de 50 MB.",
                    )
                f_out.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante la escritura del archivo en disco: {str(e)}",
        )

    if file_size == 0:
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo proporcionado está vacío (0 bytes).",
        )

    try:
        df = pd.read_csv(destination_path)
    except Exception as e:
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de formato al analizar el archivo CSV: {str(e)}",
        )

    if len(df) < 10:
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El dataset contiene muy pocos registros ({len(df)} filas). Se requiere un mínimo de 10 registros para entrenamiento.",
        )

    # Validar columnas requeridas usando la rutina compartida de normalización (Finding 2)
    norm_col_map = {normalize_column_name(c): c for c in df.columns}
    required_features = {"age", "workclass", "education_num", "marital_status", "occupation", "relationship", "race", "sex", "hours_per_week"}
    missing_features = required_features - set(norm_col_map.keys())
    if missing_features:
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo CSV carece de las siguientes columnas requeridas: {sorted(list(missing_features))}",
        )

    # Validar presencia y distribución de la columna objetivo 'income' (Finding 7)
    target_key = None
    for candidate in ["income", "class", "target"]:
        if candidate in norm_col_map:
            target_key = candidate
            break

    if not target_key:
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo CSV debe incluir obligatoriamente la columna objetivo 'income' (o 'class'/'target') con etiquetas '<=50K' y '>50K'.",
        )

    orig_target_col = norm_col_map[target_key]
    cleaned_target = df[orig_target_col].astype(str).str.strip().str.rstrip(".")
    classes_present = set(cleaned_target.unique())
    if not {">50K", "<=50K"}.issubset(classes_present):
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La columna objetivo '{orig_target_col}' debe contener ambas clases ('>50K' y '<=50K'). Encontradas: {sorted(list(classes_present))}",
        )

    counts = cleaned_target.value_counts()
    if counts.get(">50K", 0) < 5 or counts.get("<=50K", 0) < 5:
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El dataset debe contener al menos 5 registros de cada clase ('>50K' y '<=50K') para asegurar partición estratificada válida.",
        )

    row_count = len(df)

    # Registrar en base de datos con nombre de almacenamiento único (Finding 2)
    db_record = TrainingDataset(
        filename=file.filename,
        row_count=row_count,
        file_size_bytes=file_size,
        status="uploaded",
        notes=storage_filename,
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    return UploadDatasetResponse(
        status="success",
        filename=file.filename,
        rows_ingested=row_count,
        dataset_id=db_record.id,
        message="Archivo validado y registrado en training_datasets.",
    )


@router.post(
    "/retrain",
    response_model=RetrainResponse,
    status_code=status.HTTP_200_OK,
    summary="Ejecutar reentrenamiento completo CRISP-ML(Q) (Autenticado)",
    description=(
        "Dispara el pipeline asíncrono en un hilo de trabajo dedicado (off-loop) para no bloquear la API REST. "
        "Permite seleccionar un dataset específico por ID o utiliza el último dataset subido validado."
    ),
    responses={
        200: {"description": "Pipeline CRISP-ML(Q) completado y nuevo modelo activado exitosamente."},
        401: {"description": "No autorizado. Token Bearer ausente o inválido."},
        404: {"description": "Dataset solicitado o archivo base no encontrado."},
        409: {"description": "Ya existe un proceso de reentrenamiento activo."},
        500: {"description": "Error durante el reentrenamiento."},
    },
)
async def trigger_retrain(
    payload: Optional[RetrainRequest] = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if _is_retraining_lock.locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un proceso de reentrenamiento en ejecución. Espere a que finalice.",
        )

    # Determinar el archivo de dataset a utilizar (Finding 9)
    selected_dataset_id: Optional[int] = None
    target_csv_path: Optional[Path] = None

    def _resolve_dataset_path(record: TrainingDataset) -> Optional[Path]:
        if record.notes:
            cand = settings.DATA_DIR / record.notes
            if cand.exists():
                return cand
        for legacy_name in [f"uploaded_{record.filename}", record.filename]:
            cand = settings.DATA_DIR / legacy_name
            if cand.exists():
                return cand
        return None

    if payload and payload.dataset_id is not None:
        dataset_rec = db.query(TrainingDataset).filter(TrainingDataset.id == payload.dataset_id).first()
        if not dataset_rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset con ID {payload.dataset_id} no encontrado en la base de datos.",
            )
        candidate_path = _resolve_dataset_path(dataset_rec)
        if not candidate_path or not candidate_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El archivo físico asociado al dataset no se encontró en el servidor.",
            )
        selected_dataset_id = dataset_rec.id
        target_csv_path = candidate_path
    else:
        # Prioridad 1: Dataset censal completo de producción (32,561 registros)
        base_csv = settings.DATA_DIR / "adult.csv"
        if base_csv.exists():
            target_csv_path = base_csv
        else:
            # Prioridad 2: Buscar el dataset más reciente subido con estado 'uploaded'
            latest_uploaded = (
                db.query(TrainingDataset)
                .filter(TrainingDataset.status == "uploaded")
                .order_by(TrainingDataset.uploaded_at.desc(), TrainingDataset.id.desc())
                .first()
            )
            if latest_uploaded:
                cand_path = _resolve_dataset_path(latest_uploaded)
                if cand_path and cand_path.exists():
                    selected_dataset_id = latest_uploaded.id
                    target_csv_path = cand_path

    if target_csv_path is None:
        target_csv_path = settings.DATA_DIR / "adult.csv"
        if not target_csv_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset base no encontrado en {target_csv_path}. Suba un archivo CSV mediante /api/v1/train/upload primero.",
            )

    async with _is_retraining_lock:
        try:
            # 1. Notificar inicio vía WebSocket
            await emit_progress("preprocessing", 25, f"Iniciando ingesta y preprocesamiento de {target_csv_path.name}...")
            await asyncio.sleep(0.1)

            # 2. Entrenamiento
            await emit_progress("training", 50, "Ajustando clasificador Gradient Boosting con validación estratificada...")
            await asyncio.sleep(0.1)

            # 3. Pipeline de reentrenamiento offloaded a worker thread (Finding 5)
            result = await asyncio.to_thread(
                run_retrain_pipeline,
                csv_path=target_csv_path,
                dataset_id=selected_dataset_id,
            )

            # 4. Evaluación y calibración
            await emit_progress("evaluating", 75, "Evaluando métricas y optimizando umbral robusto de costo...")
            await asyncio.sleep(0.1)

            # 5. Finalización
            await emit_progress(
                "completed",
                100,
                f"Nuevo modelo {result['new_model_version']} desplegado con éxito.",
                payload=result,
            )

            return RetrainResponse(
                status="success",
                message="Pipeline CRISP-ML(Q) completado con éxito.",
                new_model_version=result["new_model_version"],
                updated_metrics=result["metrics"],
                threshold=result["threshold"],
            )
        except Exception as e:
            logger.error(f"Fallo en reentrenamiento: {e}")
            await emit_progress("error", 0, f"Error durante el pipeline: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error durante el reentrenamiento: {str(e)}",
            )
