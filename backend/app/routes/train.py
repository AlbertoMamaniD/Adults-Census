import asyncio
import io
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
import pandas as pd
from sqlalchemy.orm import Session
from app.config import settings
from app.database.connection import get_db
from app.database.models import TrainingDataset
from app.schemas.training import RetrainResponse, UploadDatasetResponse
from app.services.auth_service import get_optional_user
from app.services.retrain_service import emit_progress, run_retrain_pipeline

router = APIRouter(prefix="", tags=["Entrenamiento y MLOps"])
logger = logging.getLogger("train_routes")

# Bloqueo concurrente de reentrenamiento
_is_retraining_lock = asyncio.Lock()
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB límite


@router.post(
    "/train/upload",
    response_model=UploadDatasetResponse,
    status_code=status.HTTP_200_OK,
    summary="Cargar nuevo dataset para reentrenamiento",
    description="Sube un archivo CSV con datos censales, valida columnas obligatorias, comprueba integridad y registra el lote en la base de datos.",
)
async def upload_training_dataset(
    file: UploadFile = File(..., description="Archivo CSV del dataset de entrenamiento"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_optional_user),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato inválido. Solo se admiten archivos con extensión .csv.",
        )

    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo proporcionado está vacío (0 bytes).",
        )

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo excede el tamaño máximo permitido de 50 MB (tamaño: {file_size / (1024*1024):.2f} MB).",
        )

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de formato al analizar el archivo CSV: {str(e)}",
        )

    if len(df) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El dataset contiene muy pocos registros ({len(df)} filas). Se requiere un mínimo de 10 registros para entrenamiento.",
        )

    # Validar columnas mínimas requeridas
    required_cols = {"age", "workclass", "education_num", "marital_status", "occupation", "relationship", "race", "sex", "hours_per_week"}
    norm_cols = {c.strip().replace("-", "_") for c in df.columns}
    missing = required_cols - norm_cols
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo CSV carece de las siguientes columnas requeridas: {sorted(list(missing))}",
        )

    # Guardar archivo en disco
    data_dir = settings.DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    destination_path = data_dir / f"uploaded_{file.filename}"
    with open(destination_path, "wb") as f:
        f.write(content)

    row_count = len(df)

    # Registrar en base de datos
    db_record = TrainingDataset(
        filename=file.filename,
        row_count=row_count,
        file_size_bytes=file_size,
        status="uploaded",
        notes=f"Subido vía REST API. Filas válidas: {row_count}.",
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
    summary="Ejecutar reentrenamiento completo CRISP-ML(Q)",
    description="Dispara el ciclo completo de preprocesamiento, ajuste del modelo supervisado, optimización de umbral y despliegue del nuevo artefacto.",
)
async def trigger_retrain(
    db: Session = Depends(get_db),
    user: dict = Depends(get_optional_user),
):
    if _is_retraining_lock.locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un proceso de reentrenamiento en ejecución. Espere a que finalice.",
        )

    async with _is_retraining_lock:
        try:
            # 1. Notificar inicio vía WebSocket
            await emit_progress("preprocessing", 25, "Iniciando ingesta y preprocesamiento de datos...")
            await asyncio.sleep(0.3)

            # 2. Entrenamiento
            await emit_progress("training", 50, "Ajustando clasificador Gradient Boosting con validación estratificada...")
            await asyncio.sleep(0.3)

            # 3. Pipeline de reentrenamiento
            result = run_retrain_pipeline(db=db)

            # 4. Evaluación y calibración
            await emit_progress("evaluating", 75, "Evaluando métricas y optimizando umbral robusto de costo...")
            await asyncio.sleep(0.2)

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
